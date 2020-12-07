import sys
from types import MethodType
import logging
from functools import partial


class Logger:

    def __init__(self, logger_name, log_path, level=logging.INFO):
        self.log_path = log_path
        self.logger = logging.getLogger(logger_name)
        formatter = logging.Formatter('[%(log_type_str)s] %(asctime)s - %(msg)s', datefmt='%Y-%m-%d %H:%M:%S',
                                      style="%")
        fileHandler = logging.FileHandler(self.log_path)
        fileHandler.setFormatter(formatter)

        self.logger.setLevel(level)
        self.logger.addHandler(fileHandler)
        self.log_types = {"info":    {"log_type_str": "INFO", "func": self.logger.info},
                          "error":   {"log_type_str": "ERROR", "func": self.logger.error},
                          "debug":   {"log_type_str": "DEBUG", "func": self.logger.debug},
                          "warning": {"log_type_str": "WARN", "func": self.logger.warning},
                          "log":     {"log_type_str": "LOG", "func": self.logger.log}}

    def set_log_type_str(self, log_type, val):
        self.log_types[log_type]['log_type_str'] = val

    def set_log_func(self, log_type, val):
        self.log_types[log_type]['func'] = val

    def create_log_type_str(self, log_type, log_type_str=None):
        log_type_str = log_type if log_type_str is None else log_type_str
        self.log_types[log_type] = {"log_type_str": log_type_str, "func": self.logger.log}

    def dispatch(self, msg, *args, log_type="log", **kwargs):
        """
        用log类型分别调用对应的函数
        :param msg: 打印的Log信息主体
        :param args: optional args
        :param log_type: log类型
        :param kwargs: keyword args
        :return:
        """
        log_type_str = self.log_types[log_type]['log_type_str']
        _func = self.log_types[log_type]['func']

        _func(msg=msg, *args, extra={"log_type_str": log_type_str}, **kwargs)

    def info(self, msg):
        self.dispatch(sys._getframe().f_code.co_name, msg)

    def debug(self, msg):
        self.dispatch(sys._getframe().f_code.co_name, msg)
        pass

    def warn(self, msg):
        self.dispatch(sys._getframe().f_code.co_name, msg)
        pass

    def error(self, msg):
        self.dispatch(sys._getframe().f_code.co_name, msg)
        pass

    @staticmethod
    def _create_log_func(log_type, level=None, **kwargs):
        def function_template(cls, msg, **f_kwargs):
            cls.dispatch(msg=msg, **f_kwargs)

        return partial(function_template, log_type=log_type, level=level, **kwargs)

    def register_log_function(self, func_name: str, log_type_str: str = None, level=logging.INFO):
        """
        注册自定义log函数
        :param func_name: log函数名
        :param log_type_str: 输出日志的前缀字符串，用于标明类型
        :param level: 函数的log等级
        """
        log_type_str = func_name if log_type_str is None else log_type_str

        self.create_log_type_str(func_name)
        self.set_log_type_str(func_name, log_type_str)

        func = self._create_log_func(log_type=func_name, level=level)
        instance_func = MethodType(func, self)
        setattr(self.__class__, func_name, instance_func)
        return instance_func


if __name__ == "__main__":
    pass
