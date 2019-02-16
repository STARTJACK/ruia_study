#-*-coding:utf8-*-

import asyncio
import aiohttp
import async_timeout

from inspect import iscoroutinefunction
from types import  AsyncGeneratorType
from typing import Tuple

from ruia_study.response import Response
from ruia_study.utils import get_logger


class Request(object):
    name = 'Request'
    #请求参数设置
    REQUEST_CONFIG = {
        'RETRIES': 3,
        'DELAY': 0,
        'TIMEOUT': 10,
        'RETRY_FUNC': None,
    }

    METHOD = ['GET', 'POST']

    #初始化请求参数，请求头，请求会话，回调函数，响应类型
    def __init__(self, url: str, method:str = 'GET',*,
                 callback=None,
                 headers:dict={},
                 metadata:dict={},
                 request_config:dict=(),
                 request_session=NOne,
                 res_type:str='text',
                 **kwargs):

        self.url = url
        self.method = method.upper()
        #确保请求方法为GET或POST
        if self.method not in self.METHOD:
            raise ValueError('%s method is not supported'% self.method)

        self.callback = callback
        self.headers = headers
        self.metadata = metadata
        self.request_session = request_session
        self.request_config = request_config or self.REQUEST_CONFIG
        self.res_type = res_type
        self.kwargs = kwargs

        self.close_request_session = False
        self.logger = get_logger(name=self.name)
        self.retry_times = self.request_config.get("RETRIES", 3)

    @property #将该方法作为属性调用，创建请求函数
    def current_request_func(self):
        self.logger.info(f'<{self.method}: {self.url}>')
        # 执行请求
        if self.method == 'GET':
            request_func = self.current_request_session.get(
                self.url,
                headers=self.headers,
                verify_ssl=False,
                **self.kwargs
            )
        else:
            request_func = self.current_request_session.post(
                self.url,
                headers=self.headers,
                verify_ssl=False,
                **self.kwargs
            )
        return request_func

    @property #创建会话
    def current_request_session(self):
        if self.request_session is None:
            self.request_session = aiohttp.ClientSession()
            self.close_request_session = True
        return self.request_session

    #关闭会话
    async def close(self):
        #若请求为js渲染请求，则关闭browser
        if hasattr(self, "browser"):
            await self.browser.close()
        if self.close_request_session:
            await self.request_session.close()
            self.request_session = None

    #发起请求
    async def fetch(self) -> Response:
        res_headers, res_history = {}, ()
        res_status = 0 #响应状态码
        res_data, res_cookies = None, None
        #若设置延迟，则执行延迟
        if self.request_config.get('DELAY', 0) >0:
            await asyncio.sleep(self.request_config['DELAY'])
        try:
            #超时设置
            timeout = self.request_config.get("TIMEOUT", 10)
            async with async_timeout.timeout(timeout):
                async with self.current_request_func as resp:
                    res_status = resp.status # 状态码无需await
                    #确保响应成功，否则抛出异常
                    assert res_status in [200, 201]
                    #根据响应类型获取响应内容
                    if self.res_type =='bytes':
                        res_data = await resp.read()
                    elif self.res_type == 'json':
                        res_data = await resp.json()
                    else:
                        res_data = await resp.text()

                    #获取响应相关信息
                    res_cookies, res_headers, res_history = resp.cookies, resp.headers, resp.history
        except Exception as e:
            self.logger.error(f'<Error: {self.url} {res_status} {str(e)}')

        #处理需要重试的请求,超过请求次数则跳过此步骤
        if self.retry_times >0 and res_data is None:
            retry_times = self.request_config.get("RETRIES", 3) - self.retry_times + 1
            self.logger.info(f'<Retry url: {self.url}, Retry times: {retry_times}')
            self.retry_times -= 1
            retry_func = self.request_config.get('RETRY_FUNC')
            #若设置了重试函数，则执行重试函数
            if retry_func and iscoroutinefunction(retry_func):
                request_ins = await retrt_func(self)
                if isinstance(request_ins, Request):
                    return await request_ins.fetch()
            #否则重试原请求函数
            return await self.fetch()
        await self.close()

        response = Response(url=self.url,
                            html=res_data,
                            metadata=self.metadata,
                            res_type=self.res_type,
                            cookies=res_cookies,
                            headers=res_headers,
                            history=res_history,
                            status=res_status)
        return response


    #处理请求及回调函数
    async def fetch_callback(self, sem) -> Tuple[AsyncGeneratorType, Response]:
        #设置并发数
        async with sem:
            res = await self.fetch()
        #若含有回调函数，则将响应用回调函数处理
        if self.callback is not None:
           try:
               if iscoroutinefunction(self.callback):
                   callback_res = await self.callback(res)
                   res.callback_result = callback_res
               else:
                   callback_res = self.callback(res)
           except Exception as e:
               self.logger.error(e)
                callback_res = None
        else:
            callback_res = None
        return callback_res, res

    #格式化输出请求
    def __str__(self):
        return "<%s %s>" % (self.method, self.url)