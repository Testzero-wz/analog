from analog.bin.exception.Exceptions import *
from analog.bin.lib.utils import *
from analog.bin.lib.sql import db
from analog.bin.io.color_output import ColorOutput
import re
from analog.bin.configparser.configparser import Config


def check_txt(txt_path):
    if os.path.exists(txt_path) is False:
        raise FileNotFound
    if os.path.getsize(txt_path) == 0:
        return False
    else:
        with open(txt_path, "r", encoding='utf-8') as file:
            line = file.readline().strip("\r\n ")
            while line:
                if line != '' and line[0] == '#':
                    line = file.readline().strip("\r\n ")
                    continue
                if line != '#':
                    return True
            return False


class CheckConf:
    def __init__(self, config_path, default_config_path, root_path):
        self.config = None
        self.all_columns = ["remote_addr", "remote_user", "time_local", "request", "status", "body_bytes_sent",
                            "http_referer", "http_user_agent", "http_x_forwarded_for"]
        if os.path.exists(config_path):
            self.config = Config(config_path, default_config_path)
        else:
            raise FileNotFound("Config File Not Found")
        self.root_path = root_path
        self.db = db(self.config, self.root_path)
        self.output = ColorOutput()
        self.pattern = None
        self.section_name_log = "Log"
        self.section_name_database = "Database"

        self.pattern = self.config.get(self.section_name_log, 'log_content_pattern')

    def check_connect(self):
        try:
            _connection = self.db.connect_without_db()
            if _connection is not None:
                return 1
            else:
                return 0
        except Exception as e:
            raise e
        finally:
            self.db.close()

    def main_check(self):
        # 检查数据库连通性
        self.output.print_info("Checking [DataBase] config...")
        db_type = self.config.get(self.section_name_database, "db_type")
        self.output.print_value("db_type", db_type)
        try:
            if db_type == "mysql":
                self.check_connect()
                self.output.print_info_green("Connected DB successfully!", symbol='+')
            elif db_type == "sqlite":
                self.output.print_info_green(
                    "Skip connect test cause db_type is sqlite which is standard lib of python3")
        except Exception as e:
            self.output.print_error("Fail to connect mysql.")
            self.output.print_error(str(e))
            raise e

        # 检查正则开始
        self.output.print_info("Checking [Log] config...")
        # 检查正则是否包含最小分组
        min_group = ["remote_addr", "time_local", "request", "status"]
        log_regx = re.compile(self.pattern)
        group_index = log_regx.groupindex
        check_fail = False
        for g in min_group:
            if g not in group_index:
                self.output.print_error("Required group_name `%s` not found!" % g)
                check_fail = True
        if check_fail:
            self.output.print_error('Check your pattern!')
            exit(0)
        self.output.print_info_green("Pattern contains minimum group required!", symbol='+')
        # 检查时间格式是否达到预期
        self.output.print_info("Checking time format string...")
        # 检查正则是否达到预期效果
        self.output.print_info("Checking whether regx pattern works as expected...")
        log_path = self.config.get(self.section_name_log, 'path')
        tmp_list = []
        c = 0
        for file in fp_gen(log_path, pattern=self.config.get(self.section_name_log, "log_file_pattern")):
            if c >= 3:
                break
            try:
                self.output.print_info("+" * 15 + " Reading %s " % file.name + "+" * 15)
                read_by_group(file, tmp_list, group_name=list(group_index), pattern=self.pattern, N=1)
                if len(tmp_list) == 0:
                    self.output.print_error("Your pattern can not match any logs. Check it out.")
                    break
                _tmp = iter(tmp_list[0])
                for k in group_index:
                    if k in self.all_columns:
                        if k == "time_local":
                            self.output.print_info_green("=" * 13 + " time_local Parse Check " + "=" * 13)
                            _match_str = next(_tmp)
                            self.output.print_info("Got time_local: " + _match_str)
                            try:
                                _t = datetime.strptime(_match_str,
                                                       self.config.get(self.section_name_log, "time_local_pattern"))
                                for k, v in {
                                    "year": _t.year,
                                    "month": _t.month,
                                    "day": _t.day,
                                    "hour": _t.hour,
                                    "minute": _t.minute,
                                }.items():
                                    self.output.print_value(k, v)
                                self.output.print_info_green("=" * 10 + " Make Sure Parse Is Correctly " + "=" * 10)
                            except Exception:
                                self.output.print_error("Time_local format error.")
                        else:
                            self.output.print_value(k, next(_tmp), symbol='+')
                    else:
                        self.output.print_plain_value(k, next(_tmp), symbol='-')
            except Exception as e:
                raise e
            finally:
                c += 1
                if file is not None:
                    file.close()
        self.output.print_info_green(
            "If regx pattern works as expected and no other errors occur, indicating that your config.ini was configured correctly!",
            symbol='+')
