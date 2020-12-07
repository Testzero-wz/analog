from configparser import RawConfigParser
from configparser import NoOptionError


class Config(RawConfigParser):

    def __init__(self, config_path, default_config_path, encoding='utf-8'):
        """
        重载RawConfigParser，添加默认模板
        :param config_path: 读取的配置文件路径
        :param default_config_path: 默认配置文件路径，当config_path缺失某个字段时，会从默认配置文件中读取
        :param encoding: 打开配置文件的编码，默认utf-8
        """
        super().__init__()
        self.read(config_path, encoding=encoding)

        self.default_config_path = default_config_path
        self.default_config = RawConfigParser()
        self.default_config.read(default_config_path, encoding=encoding)

    def get(self, section, option, *args, **kwargs) -> str:
        try:
            return super().get(section, option, *args, **kwargs)
        except NoOptionError:
            return self.default_config.get(section, option, *args, **kwargs)
