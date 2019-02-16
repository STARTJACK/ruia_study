#-*-coding:utf8-*-

import os
from importlib import util
from ruia_study.utils.log import get_logger


logger = get_logger('settings')

class SettingsWrapper(object):

    def __init__(self, settings_name = 'settings.py'):
        self.my_settings = {}
        self.settings_name = settings_name
        self._load_settings()

    def __call__(self, *args, **kwargs):
        return self.my_settings

    @property
    def settings(self):
        return self.my_settings

    #从.py文件动态导入设置
    def load_with_file(self, file_path):
        file_name = os.path.basename(file_name)
        if file_name[-3:] != '.py':
            logger.error("module name must be python file, such as : example.py")
        #获取模块信息，file_path包含后缀名
        module_spec = util.spec_from_file_location(file_name, file_path)
        if module_spec is None:
            logger.error("Module path : {} not found Module: {}".format(file_name, file_path))
            return
        #导入模块信息获得模块，引入模块后调用loader.exec_module，
        # 并且运行dir(module)来确保是我们所期望的
        module = util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        #此处获取外部模块里面的设置信息
        load_settings = self._conver2dict(module)
        self.my_settings.update(load_settings)


    #从定义的字典导入设置
    def load_with_dict(self, dict_params):
        self.my_settings.update(dict_params)

    #从环境变量中导入
    def load_from_environment(self, prefix='RUIA_'):
        env_dict = {}
        #os.environ.items()将会获取环境变量字典集合
        for k, v in os.environ.items():
            #若前缀包含RUIA_则符合要求，由于设置里包含int,float,str三种类型
            if k.startswith(prefix):
                _, config_key = k.split(prefix, 1)
                try:
                    env_dict[config_key] = int(v)
                except ValueError:
                    try:
                        env_dict[config_key] = float(v)
                    except ValueError:
                        env_dict[config_key] = v
        self.my_settings.update(env_dict)


    #导入默认设置
    def _load_settings(self):
        try:
            module = self._dynamic_import(self._closest_file(self.settings_name))
            self.my_settings = self._convert2dict(module)
        except ImportError:
            logger.warning('No default settings found')

    #动态导入设置，与上面描述类似
    def _dynamic_import(self, module_path):
        basename = os.path.basename(module_path)

        # if basename[-3:] == '.py':
        #     basename = basename[:-3]

        module_spec = util.spec_from_file_location(basename, module_path)

        if module_spec is None:
            logger.error("Module path: {} not found Module:{}".format(module_path, basename))
            return

        module = util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module

    #获取模块的属性值
    def _convert2dict(self, module):
        res = {}
        m = dir(module)
        for key in m:
            if key.startswith('__'):
                continue
            value = getattr(module, key)
            res[key] = value
        return res

    #获取相邻最近的设置文件,当前目录没找到，则往上找
    def _closest_file(self, file_name='settings.py', path='.', prev_path=None ):

        #递归结束，没有找到该文件
        if path == prev_path:
            return
        #返回绝对路径
        path = os.path.abspath(path)
        settings_file = os.path.join(path, file_name)
        if os.path.exists(settings_file):
            return settings_file
        return self._closest_file(file_name=file_name, path=os.path.dirname(path), prev_path=path)


if __name__ == '__main__':
    setting = SettingsWrapper()
    module = setting._load_settings()