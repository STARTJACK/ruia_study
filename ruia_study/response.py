#-*-coding:utf8-*-

from lxml import etree

class Response(object):

    #初始化参数
    def __init__(self, url: str, *,
                 metadata:dict,
                 res_type: str,
                 html: str ='',
                 cookies,
                 history,
                 headers:dict = None,
                 status: int):

        self._callback_result = None
        self._url = url
        self._metadata = metadata
        self._res_type = res_type
        self._html = html
        self._cookies = cookies
        self._history = history
        self._headers = headers
        self._status = status


    #以下将其方法当作属性调用
    @property
    def callback_result(self):
        return self._callback_result

    @callback_result.setter
    def callback_result(self, value):
        self._callback_result = value

    @property
    def url(self):
        return self._url

    @property
    def metadata(self):
        return self._metadata

    @property
    def res_type(self):
        return self._html

    @property
    def html(self):
        return self._html

    @property
    def cookies(self):
        return self._cookies

    @property
    def history(self):
        return self._history

    @property
    def headers(self):
        return self._headers

    @property
    def status(self):
        return self._status

    @property #返回html_etree对象
    def html_etree(self):
        html_etree = None
        if self.html:
            html_etree = etree.HTML(self.html)
        return html_etree

    def __str__(self):
        return f'<Response url[{self._res_type}]'