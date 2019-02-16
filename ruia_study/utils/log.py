#-*-coding:utf8-*-

import logging

def get_logger(name='Ruia'):
    #日志格式
    logging_format = "[%(asctime)s]-%(name)s-%(levelname)-6s"
    logging_format += "%(module)-7s: "
    logging_format += "%(message)s"

    #日志配置
    logging.basicConfig(
        format = logging_format,
        level = logging.DEBUG,
    )

    #此处将下面三个模块的info级别以下及debug信息不打印到控制台
    logging.getLogger('asyncio').setLevel(logging.INFO)
    logging.getLogger('pyppeteer').setLevel(logging.INFO)
    logging.getLogger('websockets').setLevel(logging.INFO)

    return logging.getLogger(name)


if __name__ == '__main__':
    logger = get_logger('asyncio')
    logger.debug("debug")