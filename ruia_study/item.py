#-*-coding:utf8-*-

from inspect import iscoroutinefunction
from lxml import etree
from typing import Any

from ruia_study.field import BaseField
from ruia.request import Request


#创建自定义元类，必须继承type,用于控制生成类实例的过程
class ItemMeta(type):

    #继承元类，__new__方法的参数为name，bases，attrs
    def __new__(cls, name, bases, attrs):
        #将自定义的符合要求的字段传递到生成类实例过程中
        __fields = dict({
            (field_name, attrs.pop(field_name)) for field_name, object in list(attrs.items())
                if isinstance(object, BaseField)
        })
        attrs['__fields'] = __fields
        new_class = type.__new__(cls, name, bases, attrs)
        return new_class


class Item(metaclass=ItemMeta): #必须传递metaclass才能使用自定义的元类生成实例

    def __init__(self):
        self.results = {}


    @classmethod #获取etree对象
    async def _get_html(cls, html, url, **kwargs):
        if html is None and not url:
            raise ValueError("html(url or html_etree")
        if not html:
            request = Request(url, **kwargs)
            response = await request.fetch()
            html = response.html
        return etree.HTML(html)

    @classmethod #获取包含单个数据的item实例
    async def get_item(cls, *, html:str='', url:str='', html_etree: etree._Element = None, **kwargs) -> Any:
        if html_etree is None:
            etree_result = await cls._get_html(html, url, **kwargs)
        else:
            etree_result = html_etree
        return await cls._parse_html(etree_result)


    @classmethod #获取含多字段数据的item实例
    async def get_items(cls, *, html:str='', url: str ='',html_etree:etree._Element =None,**kwargs) -> list:
        if html_etree is None:
            etree_result = await cls._get_html(htm, url, **kwargs)
        else:
            etree_result = html_etree
        #必须设置target字段，target为所有字段的共同部分
        #即之后设置的字段都是在target字段为基础上的
        items_field = getattr(cls, '__fields', {}).get('target_item', None)
        if items_field:
            #此处is_source=True，表示直接提取该节点就返回
            items = items_field.extract_value(etree_result, is_source=True)
            if items:
                #将目标节点传入解析方法中并提取数据
                tasks = [cls._parse_html(etree_result=i) for i in items]
                all_items = []
                #遍历任务列表并执行解析任务最后返回含数据的item实例
                for task in tasks:
                    all_items.append(await task)
                return all_items
            else:
                raise ValueError("Get target_item's value error!")
        else:
            raise ValueError("target_item is expected")


    @classmethod #解析数据并返回item实例
    async def _parse_html(cls, etree_result:etree._Element) -> object:
        #确保传入etree._Element对象
        if etree_result is None or not isinstance(etree.result, etree._Element):
            raise ValueError("etree._Element is expected")
        item_ins = cls()
        #根据自定义的字段解析数据
        for field_name, field_value in getattr(item_ins, '__fields', {}).items():
            #对自定义字段数据进行处理，相当于scrapy的itempipeline功能
            clean_method = getattr(item_ins, 'clean_%s' % field_name, None)
            #提取数据，若定义了提取方法则调用，否则返回原数据值
            value = field_value.extract_value(etree_result) if isinstance(field_value, BaseField) else field_value
            if clean_method is not None:
                #若为协程，则await
                if iscoroutinefunction(clean_method):
                    value = await clean_method(value)
                else:
                    value = clean_method(value)
            #将字段提取方法设置为真实数据
            setattr(item_ins, field_name, value)
            item_ins.results[field_name] = value
        return item_ins


    def __str__(self):
        return f'<Item {self.results}>'