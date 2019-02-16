#-*-coding:utf8-*-

from collections import deque #双端队列，及队列前后均可操作
from functools import wraps

class Middleware:

    # 初始化请求中间件和响应中间件
    def __init__(self):
        self.request_middleware = deque()
        self.response_middleware = deque()

    #装饰器，将自定义的请求或响应中间件添加到相应的中间件队列中
    def listener(self, uri, target, **kwargs):

        def register_middleware(middleware):
            if target == 'request':
                self.request_middleware.append(middleware)
            if target == 'response':
                self.response_middleware.append(middleware)
            return middleware
        return register_middleware

    #装饰器， 将自定义的请求中间件添加到请求中间件队列
    def request(self, *args, **kwargs):
        middleware = args[0]

        @wraps(middleware)
        def register_middleware(*args, **kwargs):
            self.request_middleware.append(middleware)
            return middleware
        return register_middleware()

    # 装饰器， 将自定义的响应中间件添加到响应中间件队列
    def response(self, *args, **kwargs):
        middleware = args[0]

        @wraps(middleware)
        def register_middleware(*args, **kwargs):
            self.response_middleware.append(middleware)
            return middleware

        return register_middleware()

    #将多个中间件的请求中间件和响应中间件分别合并
    def __add__(self, other):
        new_middleware = Middleware()

        new_middleware.request_middleware.extend(self.request_middleware)
        new_middleware.request_middleware.extend(other.request_middleware)

        new_middleware.response_middleware.extend(self.response_middleware)
        new_middleware.response_middleware.extend(other.response_middleware)

        return new_middleware

