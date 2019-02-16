#-*- coding:utf8-*-

from lxml import etree

#基类
class BaseField(object):

    def __init__(self, css_select=None, xpath_select=None, default=None):
        self.css_select = css_select
        self.xpath_select = xpath_select
        self.default = default

#获取文本
class TextField(BaseField):
    def __init__(self, css_select=None, xpath_select=None, defalut=None):
        super().__init__(css_select, xpath_select, defalut)

    #提取数据
    def extract_value(self, html, is_source=False):
        #判断解析类型
        if self.css_select:
            value = html.cssselect(self.css_select)
        elif self.xpath_select:
            value = html.xpath(self.xpath_select)
        else:
            raise ValueError("%s field: css_select or xpath_select is respected"% self.__class__.__name__)
        if is_source:
            return value
        #判断提取的节点是否为list且元素个数为1,此处的value可以是公共节点target_item，或单个节点
        if isinstance(value, list) and len(value) == 1:
            text = ''
            if isinstance(value[0], etree._Element):
                for node in value[0].itertext():
                    text += node.strip()
            if isinstance(value[0], str) or isinstance(value, etree._ElementUnicodeResult):
                text = ''.join(value)
            value = text
        #判断是否使用默认值
        if self.default is not None:
            value = value if value else self.default
        return value


#参照TextField分析
class AttrField(BaseField):

    def __init__(self, attr, css_select=None, xpath_select=None, default=None):
        super(AttrField, self).__init__(css_select, xpath_select, default)
        self.attr = attr

    def extract_value(self, html, is_source=False):
        """
        Use css_select or re_select to extract a field value
        :return:
        """
        if self.css_select:
            value = html.cssselect(self.css_select)
            value = value[0].get(self.attr, value) if len(value) == 1 else value
        elif self.xpath_select:
            value = html.xpath(self.xpath_select)
        else:
            raise ValueError('%s field: css_select or xpath_select is expected' % self.__class__.__name__)
        if is_source:
            return value
        if self.default is not None:
            value = value if value else self.default
        return value

