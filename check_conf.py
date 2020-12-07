from analog.bin.check.check import CheckConf
import os


def main():
    root_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(root_path, 'config.ini')
    default_config_path = os.path.join(root_path, "analog/conf/default_config.ini")
    checker = CheckConf(config_path=config_path,
                        default_config_path=default_config_path,
                        root_path=root_path)
    checker.main_check()


if __name__ == "__main__":
    main()
    pass
