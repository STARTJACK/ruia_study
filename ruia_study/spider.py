#-*-coding:utf8-*-

import asyncio

from functools import reduce
from inspect import isawaitable
from datetime import datetime
from types import AsyncGeneratorType

class Spider:
    #爬虫名称
    name = 'ruia'
    #初始urls, 初始任务列表
    start_urls, worker_tasks = [], []
    #请求配置，包括重试次数，超时限制，请求延迟秒数
    request_config = None
    #请求成功数、失败数
    failed_counts, success_counts = 0, 0
    #concurrency并发数可单独设置，默认为3


    #初始化中间件，事件循环，日志，并发数，请求队列
    def __init__(self,middleware=None, loop=None):
        #确保初始urls存在且为list
        if not self.start_urls or not isinstance(self.start_urls, list):
            raise ValueError("Spider must have a param named start_urls, eg: start_urls = ['https://www.github.com']")
        #初始化日志
        self.logger = get_logger(name=self.name)
        #初始化事件循环
        self.loop = loop or asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        #将传入的请求、相应中间件列表进行合并(合并方法见middleware类的__add_方法，主要是将请求和响应中间件分开)
        if isinstance(middleware, list):
            self.middleware = reduce(lambda x, y: x+y, middleware)
        else:
            self.middleware = middleware or Middleware()
        #ascyncio队列
        self.request_queue = asyncio.Queue()
        #并发数,默认为3
        self.sem  = asyncio.Semaphore(getattr(self, 'concurrency', 3))

    #必须实现parse，否则抛出未实现异常
    async def parse(self,res):
        raise NotImplementedError

    @classmethod  #爬虫开始入口
    def start(cls, after_start=None, before_stop=None,middleware=None, loop=None, close_event_loop=True):
        """
        Start a spider
        :param after_start:
        :param before_stop:
        :param middleware:
        :param loop:
        :param close_event_loop:
        :return:
        """
        #创建新的Spider实例
        spider_ins = cls(middleware=middleware, loop=loop)
        spider_ins.logger.info('Spider started')
        start_time = datetime.now()

        if after_start:
            func_after_start = after_start(spider_ins)
            if isawaitable(func_after_start):
                spider_ins.loop.run_until_complete(func_after_start)

        #Linux平台上关于终止信号处理协程的方法
        for _signal in (SIGINT, SIGTERM):
            try:
                spider_ins.loop.add_signal_handler(_signal, lambda: asyncio.ensure_future(spider_ins.stop(_signal)))
            except NotImplementedError:
                spider_ins.logger.warning(f'{spider_ins.name} tried to use loop.add_signal_handler '
                                          'but it is not implemented on this platform.')
        #任务封装并开始
        asyncio.ensure_future(spider_ins.start_master())
        try:
            spider_ins.loop.run_forever()  #由于任务封装的方法包含loop.stop()，故执行完毕后会退出循环
        finally:
            #若定义了停止协程前需完成的方法
            if before_stop:
                func_before_stop = before_stop(spider_ins)
                if isawaitable(func_before_stop):
                    spider_ins.loop.run_until_complete(func_before_stop)

            end_time = datetime.now()
            spider_ins.logger.info(f'Total requests: {spider_ins.failed_counts + spider_ins.success_counts}')
            #统计失败请求数
            if spider_ins.failed_counts:
                spider_ins.logger.info(f'Failed requests: {spider_ins.failed_counts}')
            spider_ins.logger.info(f'Time usage: {end_time-start_time}')
            spider_ins.logger.info('Spider finished!')
            spider_ins.loop.run_until_complete(spider_ins.loop.shutdown_asyncgens())
            if close_event_loop:
                spider_ins.loop.close()


    #中间件处理请求并发送和处理响应
    async def handle_request(self, request):
        await self._run_request_middleware(request)
        callback_res, response = await request.fetch_callback(self.sem)
        await self._run_response_middleware(request, response)
        return callback_res, response




    #任务开始入口
    async def start_master(self):
        for url in self.start_urls:
            #初始化Request实例
            request_ins = Request(url=url,
                                  callback=self.parse,
                                  headers=getattr(self, 'headers', {}),
                                  metadata=getattr(self, 'metadata', {}),
                                  request_config=getattr(self, 'request_config'),
                                  request_session=getattr(self, 'request_session', None),
                                  res_type=getattr(self, 'res_type', 'text'),
                                  **getattr(self, 'kwargs', {}))
            #将由中间件处理过的request塞入request队列
            self.request_queue.put_nowait(self.handle_request(request_ins))
        #定义任务由两个工人完成
        workers = [asyncio.ensure_future(self.start_worker()) for i in range(2)]
        #确保队列请求完毕
        await self.request_queue.join()
        await self.stop(SIGINT)


    #执行任务
    async def start_worker(self):
        while True:
            request_item = await self.request_queue.get()
            #将任务塞入任务列表
            self.worker_tasks.append(request_item)
            #任务提取完毕后才执行
            if self.request_queue.empty():
                #此处使用gather，若出错，返回错误信息，继续执行其他协程
                results = await asyncio.gather(*self.worker_tasks, return_exceptions=True)
                for task_result in results:
                    #对没有RuntimeError的结果进行下一步处理
                    if not isinstance(task_result, RuntimeError):
                        callback_res, res= task_result
                        #若回调函数为协程生成器，则还有request产生，继续塞入请求队列
                        if isinstance(callback_res, AsyncGeneratorType):
                            async for request_ins in callback_res:
                                self.request_queue.put_nowait(self.handle_request(request_ins))
                        if res.html is None:
                            self.failed_counts += 1
                        else:
                            self.success_counts += 1
                #恢复任务列表，执行下一次循环
                self.worker_tasks = []
            #队列完成后的标志，否则将会一直被阻塞
            self.request_queue.task_done()


    #爬虫停止后续工作
    async def stop(self, _signal):
        self.logger.info(f'Stopping spider :{self.name}')
        #取消除当前任务以外的任务
        tasks = [task for task in asyncio.Task.all_tasks() if task is not
                 asyncio.tasks.Task.current_task()]
        list(map(lambda task:task.cancel(), tasks))
        #此处gather确保取消一些任务后而不影响未取消的任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        #停止事件循环前为避免异常需执行上述操作
        self.loop.stop()


    #请求中间件处理
    async def _run_request_middleware(self, request):
        if self.middleware.request_middleware:
            for middleware in self.middleware.request_middleware:
                middleware_func = middleware(request)
                if isawaitable(middleware_func):
                    try:
                        result = await middleware_func
                    except Exception as e:
                        self.logger.exception(e)
                else:
                    self.logger.error('Middleware must be coroutine function!')
                    result = None

    #响应中间件处理
    async def _run_response_middleware(self, request, response):
        if self.middleware.response_middleware:
            for middleware in self.middleware.response_middleware:
                middleware_func = middleware(request, response)
                if isawaitable(middleware_func):
                    try:
                        result = await middleware_func
                    except Exception as e:
                        self.logger.exception(e)
                else:
                    self.logger.error('Middleware must be a coroutine function')
                    result = None
