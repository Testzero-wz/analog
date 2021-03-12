# coding:utf-8
import traceback
from analog.bin.lib.sql import db
from analog.bin.io.color_output import ColorOutput
from analog.bin.exception.Exceptions import *
from analog.bin.machine_learning.train import Train
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.filters import Condition
from dateutil.relativedelta import relativedelta
# import configparser
from analog.bin.configparser.configparser import Config
from prompt_toolkit.formatted_text import FormattedText, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings, ConditionalKeyBindings
from analog.bin.io.completer import AnalogCompleter
from analog.bin.lib.statistics import Statistics
from analog.bin.lib.log import Logger
from analog.bin.lib.ipdatabase import ipDatabase
import multiprocessing
from analog.bin.lib.utils import *
from analog.bin.machine_learning.TfidfVector import TfidfVector
from analog.bin.check.check import check_txt
from analog.bin.lib.analysis import Analyser
import pickle
from datetime import timedelta
from analog.bin.supervisor.supervisor import FileSupervisor
from queue import Queue, Empty
from threading import Thread

NORMAL_MODE = 1
LOGGING_MODE = 2

from time import sleep


class Controller:
    analog_completer = AnalogCompleter(
        [
            ['show', 'set', 'get', 'train', 'retrain', 'locate', 'clear', 'help', 'exit'],
            ['statistics', 'analysis', 'log', "time", "offset", "progress", "model"],
            ['requests', 'ip', 'ua', 'url'],
            ['current'],
            ['day', 'week', 'month', 'year', 'all'],
            ['top']
        ],
        ignore_case=True,
    )
    style = Style.from_dict({
        # User input (default text).
        '': '#ff0066',
        # Prompt.
        'yellow': 'yellow',
        'green': 'green',
        'blue': 'blue',
        'black': 'black',
        'white': 'white',
        'analog': 'yellow',
        'help': 'blue',
        'cyan': 'ansicyan',
        'help_title': 'red',
    })
    analog_prompt = [
        ('class:yellow', 'analog> '),
    ]

    def __init__(self, path=None, debug=False):

        # 配置文件初始化
        self.path = path
        self.debug = debug
        self.config_path = os.path.join(self.path, "config.ini")
        self.default_config_path = os.path.join(self.path, "analog/conf/default_config.ini")
        self.all_columns = ["remote_addr", "remote_user", "time_local", "request", "status", "body_bytes_sent",
                            "http_referer", "http_user_agent", "http_x_forwarded_for"]

        self.time = datetime.now()
        self.output = ColorOutput()
        self.output.print_banner("AnaLog")

        if os.path.exists(self.config_path):
            self.config = Config(self.config_path, self.default_config_path)
        else:
            raise DatabaseConfigError

        # 日志参数初始化
        self.section_name_log = "Log"
        self.log_path = self.config.get(self.section_name_log, 'path')
        self.time_local_pattern = self.config.get(self.section_name_log, "time_local_pattern")
        self.log_file_pattern = self.config.get(self.section_name_log, "log_file_pattern")
        self.log_pattern = self.config.get(self.section_name_log, 'log_content_pattern')
        self.log_regx = re.compile(self.log_pattern)
        self.acceptable_group_name = list(filter(lambda x: x in self.all_columns, self.log_regx.groupindex))

        # 数据初始化
        self.db = db(self.config, root_path=self.path)
        self.logger = None
        self.analyser = None
        self.section_name_database = "database"
        self.table_name = self.config.get(self.section_name_database, "table_name")
        self.ip_db = ipDatabase(os.path.join(self.path, "analog/ipdb/ip.ipdb"))
        self.pool = None

        # 创建数据库
        if self.config.get(self.section_name_database, 'initial') != '1':
            self.init_database()
            self.config.set(self.section_name_database, 'initial', '1')

            self.init_table()
            self.config.write(open(self.config_path, "w"))
        else:
            # 连接数据库
            try:
                self.db.connect_db()
            except Exception as e:
                self.output.print_error(e)
                self.output.print_error(
                    "Connect DB failed. Please check your config file or make sure DB server is running.")
                self.output.print_info("Bye~")
                exit(0)
            self.output.print_info(
                "Logs had been loaded before.Type " + self.output.Fore.BLUE + "reload" +
                self.output.Style.RESET_ALL + self.output.Fore.LIGHTYELLOW_EX + " command to reload logs.")

        self.statistic = Statistics(database=self.db, output=self.output, ipdb=self.ip_db, controller=self)

        self.session = PromptSession()
        self.mode = NORMAL_MODE
        self.key_bindings = None

        # TF-IDF向量填充词料库
        tfidf_exist_flag = False
        self.tfidfVector = None
        try:
            self.tfidfVector = TfidfVector(self.path, self.config)
            tfidf_exist_flag = True
        except FileEmptyError:
            print_formatted_text(
                HTML('<yellow>Detected that train.txt content is empty. '
                     '<red>Disable abnormal detection.</red></yellow>'),
                style=self.style)
        except FileNotFound:
            print_formatted_text(
                HTML('<yellow>Detected that train.txt does no exist. '
                     '<red>Disable abnormal detection.</red></yellow>'),
                style=self.style)

        self.model = None
        self.progress_queue = None
        self.train_progress = None

        # 模型缓存载入
        if tfidf_exist_flag is False:
            print_formatted_text(
                HTML('<yellow>Cause of you lack of TF-IDF corpus'
                     '(<red>analog/sample_set/train.txt</red>), We can\'t calculate TF-IDF value'
                     'of each log item and can\'t use train model also</yellow>'),
                style=self.style)
        if self.check_model_cache_exist():
            print_formatted_text(
                HTML('<yellow>Detection model cache file exist. Load model from it.\nYou can type '
                     '<blue>retrain</blue> to train a new model.</yellow>'),
                style=self.style)
            self.load_model()

        # else:
        #     try:
        #         if self.train() is False:
        #             print_formatted_text(
        #                 HTML('<yellow>Train Failed! Cause of lack of train sample. '
        #                      '\nVisit <blue>https://www.testzero-wz.com</blue> for help.</yellow>'),
        #                 style=self.style)
        #     except Exception as e:
        #         raise e

        # 审计模块和分析模块初始化
        self.logger = Logger(database=self.db, output=self.output, section_name_log=self.section_name_log,
                             ipdb=self.ip_db, controller=self, tfidfvector=self.tfidfVector, config=self.config,
                             model=self.model)
        self.analyser = Analyser(database=self.db, ipdb=self.ip_db,
                                 controller=self, tfidfvector=self.tfidfVector, model=self.model)

        # 日志文件监视模块初始化
        self.file_queue = Queue()
        self.supervisor = FileSupervisor(_path=self.log_path,
                                         _queue=self.file_queue,
                                         log_path=os.path.join(self.path, "analog/logs/file_log.log"))
        # 监视线程和更新日志线程开启
        self.supervisor.start()
        self.output.print_info("Supervisor on.")
        self.update_thread = Thread(target=self.update_thread_func, daemon=True)
        self.update_thread_stop_flag = False
        self.update_thread.start()
        self.output.print_info("Updater on.")

    def mainloop(self):
        self.key_bindings = KeyBindings()

        @Condition
        def is_logging_mode():
            return self.mode == LOGGING_MODE

        @self.key_bindings.add('up')
        def _(event):
            self.clear_screen()
            self.logger.show_log(decrease=True)
            self.output.print_info("Log Mode")
            print_formatted_text(
                HTML('<yellow>[+] Press <blue>↑</blue> or <blue>↓</blue> to turn pages or '
                     '<blue>Esc</blue> to quit log mode</yellow>'),
                style=self.style)
            print_formatted_text(FormattedText(self.analog_prompt), end="")

        @self.key_bindings.add('down')
        def _(event):
            self.clear_screen()
            self.logger.show_log(increase=True)
            self.output.print_info("Log Mode")
            print_formatted_text(
                HTML('<yellow>[+] Press <blue>↑</blue> or <blue>↓</blue> to turn pages or '
                     '<blue>Esc</blue> to quit log mode</yellow>'),
                style=self.style)
            print_formatted_text(FormattedText(self.analog_prompt), end="")

        @self.key_bindings.add('escape')
        def _(event):
            self.mode = NORMAL_MODE
            self.logger.clear()
            print()
            self.output.print_info("Back to normal mode.")

        self.key_bindings = ConditionalKeyBindings(
            key_bindings=self.key_bindings,
            filter=is_logging_mode)

        while True:
            text = None
            try:
                text = self.session.prompt(self.analog_prompt, style=self.style, completer=self.analog_completer,
                                           key_bindings=self.key_bindings, refresh_interval=True)
                self.command_parser(text)

            except KeyboardInterrupt:
                if self.mode == NORMAL_MODE:
                    self.output.print_info("Are you wanna exit? Type 'exit' to quit the analog.")
                else:
                    self.output.print_lastLine("Press key Esc to quit log mode.")
            except AddCommandError:
                self.add_command_help()
            except CommandFormatError:
                self.output.print_error(
                    "Unknown command: {}. Type \"help\" for help.".format(
                        text if text else "(Failed to read command)"))
            except Exception as e:
                if self.debug:
                    traceback.print_exc()
                    raise e
                self.output.print_error("Error: %s" % str(e))

    def train(self):
        if not self.check_train_txt():
            return False
        model_train = Train(self.path, config=self.config, test_flag=False)
        self.progress_queue = multiprocessing.Manager().Queue()
        self.pool = multiprocessing.Pool(1)
        self.pool.apply_async(model_train.get_model, args=(self.progress_queue,), callback=self.train_complete_callback,
                              error_callback=self.train_error_callback)
        self.pool.close()
        self.train_progress = 0
        print_formatted_text(
            HTML('<yellow>Start the model training process.'
                 '\nYou can type <blue>get progress</blue> to get the progress of training.</yellow>'),
            style=self.style)

    def train_error_callback(self, e):
        if self.debug:
            traceback.print_exc()
        self.output.print_error(str(e))
        raise e

    def check_train_txt(self):
        train_log_path = os.path.join(self.path, "analog/sample_set/train.txt")
        test_black_path = os.path.join(self.path, "analog/sample_set/test_black_log.txt")
        test_raw_path = os.path.join(self.path, "analog/sample_set/test_white_log.txt")
        check_path = [train_log_path, test_black_path, test_raw_path]
        flag = True
        for path in check_path:
            try:
                if check_txt(path) is False:
                    flag = False
                    print_formatted_text(
                        HTML('<yellow>Necessary file ' + path + ' is <red>empty</red> ! </yellow>'),
                        style=self.style)
            except FileNotFound:
                print_formatted_text(
                    HTML('<yellow>Necessary file ' + path + '  <red>Not found</red> ! </yellow>'
                                                            '\nGenerate file automatically.'),
                    style=self.style)
        return flag

    def train_complete(self):
        self.load_model()
        print_formatted_text(
            HTML('\n\n<blue>Training task completed! '
                 'Try to type command <white>show analysis</white> to show '
                 'abnormal analysis!</blue>'), style=self.style)
        self.logger.model = self.model

    def print_train_progress(self):
        progress = float(self.get_train_progress()) * 100
        if progress == 100:
            self.train_complete()
        else:
            self.output.print_info(
                "Now train progress is {:0.2f}%".format(progress))

    def print_time(self):
        self.output.print_value("time", self.time.strftime("%Y/%m/%d %H:00:00"))

    def train_complete_callback(self, e):
        self.load_model()
        self.train_progress = 1
        self.output.print_special("Training  completed.")

    def load_model(self):
        with open(os.path.join(self.path, r'analog/cache/model.pkl'), 'rb') as file:
            self.model = pickle.load(file)
        if self.logger is not None:
            self.logger.model = self.model
        if self.analyser is not None:
            self.analyser.model = self.model

    def command_parser(self, command: str):
        """
        命令解析
        """
        command = command.lower().split()
        if len(command) == 0:
            return
        try:
            c = command[0]
            if c == 'show':
                if command[1] == 'statistics':
                    if command[2] == 'requests':
                        self.statistic.requests_num(command[4], True if command[3] == 'current' else False,
                                                    True if command[-1] == 'c' else False)
                    else:
                        if len(command) >= 7:
                            N = command[6]
                            self.statistic.top_n(command[2], command[4],
                                                 current_flag=(True if command[3] == 'current' else False), N=N)
                        else:
                            self.statistic.top_n(command[2], command[4],
                                                 current_flag=(True if command[3] == 'current' else False))
                elif command[1] == 'analysis':
                    if command[2] == 'current':
                        self.analyser.show_analysis(command[3])

                elif command[1] == 'log':
                    flag = False
                    if command[2] == 'of' and command[3] == 'ip':
                        self.logger.clear()
                        self.logger.set_mode('ip')
                        self.logger.set_ip(command[4])
                        flag = self.logger.show_log()

                    elif command[2] in ['current', 'last']:
                        self.logger.clear()
                        self.logger.set_mode('date')
                        flag = self.logger.show_log(when=command[3],
                                                    current_flag=True if command[2] == 'current' else False)

                    self.mode = LOGGING_MODE if flag else NORMAL_MODE

            elif c == 'set':
                if command[1] == 'date':
                    t = datetime.strptime(command[2], "%Y/%m/%d")
                    self.output.print_changed("time", self.set_time(
                        year=t.year, month=t.month, day=t.day, hour=t.hour).strftime("%Y/%m/%d %H:00:00"))
                elif command[1] in ['hour', 'day', 'month', 'year']:
                    d = dict()
                    d[command[1]] = int(command[2])
                    self.output.print_changed("time", self.set_time(**d).strftime("%Y/%m/%d %H:00:00"))
                    del d
                elif command[1] == 'offset':
                    self.logger.set_offset(int(command[2]))
                else:
                    raise CommandFormatError

            elif c == 'get':
                if command[1] == "time":
                    self.print_time()
                elif command[1] == "date":
                    self.output.print_value("time", self.time.strftime("%Y/%m/%d"))
                elif command[1] == "progress":
                    self.print_train_progress()
                elif command[1] == 'offset':
                    self.output.print_value("offset", self.logger.offset)
                elif command[1] == 'model':
                    if self.model:
                        params = self.model.get_params('nu')
                        print_formatted_text(FormattedText([('class:yellow', 'nu: {}'.format(params.get('nu')))]),
                                             style=self.style)
                        print_formatted_text(
                            FormattedText([('class:yellow', 'gamma: {}'.format(params.get('gamma')))]),
                            style=self.style)
                    else:
                        self.output.print_info("No model has been loaded.")
            elif c == 'train' or c == 'retrain':
                if self.train_progress is not None and self.train_progress != 1:
                    self.output.print_warning("A training task is running.")
                    self.print_train_progress()
                elif len(command) == 1:
                    if self.model is not None:
                        self.output.print_warning("Model has been loaded before!")
                        self.output.print_warning("Overwrite this model?[N/y]")
                        ans = input()
                        if ans.lower() not in ["y", "yes"]:
                            return
                    self.train()
            elif c == "locate":
                if command[1] == 'ip':
                    self.output.print_value(command[2], "-".join(self.statistic.ip_geolocation(command[2])))
            elif c == 'clear':
                self.clear_screen()
            elif c == 'help':
                self.help()
            elif c == 'debug':
                self.debug = True
                self.output.print_info("Debug mode [On].")
            elif c == 'exit':
                self.output.print_info("Bye~")
                exit(0)

            elif c == 'reload':
                self.output.print_warning("Reload option will duplicate your logs if you don't erase DB table first.")
                self.output.print_warning("Would you like to erase table?[Y/n]")
                res = input()
                if res.lower() != "n":
                    self.erase_table(self.table_name)
                    self.output.print_warning("Erased table `%s`." % self.table_name)
                self.config.set(self.section_name_database, 'initial', '0')
                self.config.write(open(self.config_path, "w"))
                self.output.print_info("Please start analog once again.")
                exit(0)
            elif c == "test":
                self.test()
            elif c == "add":
                keys = {
                    "day": "days",
                    "d": "days",
                    "hour": "hours",
                    "h": "hours",
                    "week": "weeks",
                    "w": "weeks",
                    "month": "months",
                    "m": "months",
                    "year": "years",
                    "y": "years",
                    "offset": "offset",
                    "o": "offset",
                }
                try:
                    val = None
                    key = command[1].lower()
                    if len(command) == 3:
                        val = int(command[2].lower())

                    if key not in keys:
                        raise AddCommandError
                    if keys[key] == "offset":
                        if val is None:
                            val = 5
                        self.logger.set_offset(self.logger.offset + val)
                        self.output.print_value("offset", self.logger.offset)
                    elif keys[key] in ['hours', 'days', 'weeks', 'months']:
                        if val is None:
                            val = 1
                        self.time = self.time + timedelta(**{keys[key]: val})
                        self.print_time()
                    elif keys[key] == "years":
                        # timedelta can't not handle time delta are years
                        # there aren't a explicit length of year.
                        if val is None:
                            val = 1
                        self.set_time(year=self.time.year + val)
                        self.print_time()
                except Exception as e:
                    raise AddCommandError
            else:
                raise CommandFormatError("Command not match.")
        except IndexError:
            raise CommandFormatError
        except Exception as e:
            raise e

    def erase_table(self, table_name):
        sql = "truncate table `%s`;" % table_name
        self.db.execute(sql)
        self.db.commit()
        pass

    @staticmethod
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')

    def init_database(self):
        """
        数据库初始化，数据库创建以及表创建
        """
        self.db.create_db()
        conn = self.db.connect_db()
        cursor = conn.cursor()

        # Create Table: weblog
        sql = """CREATE TABLE IF NOT EXISTS %s (
                             remote_addr  CHAR(15) NOT NULL ,
                             remote_user  VARCHAR(20),
                             time_local DATETIME DEFAULT '1970-01-01 00:00:00',
                             request TEXT DEFAULT NULL,
                             status  SMALLINT  UNSIGNED DEFAULT 0, 
                             body_bytes_sent INT DEFAULT 0,
                             http_referer TEXT,
                             http_user_agent TEXT,
                             http_x_forwarded_for TEXT);
                             """ % self.table_name
        cursor.execute(sql)
        conn.commit()
        conn.close()
        self.output.print_info("Initial database => Done.")

    def init_table(self):
        """
        数据库表单载入初始化
        将日志载入数据库中
        """

        sql = "INSERT INTO %s (%s) VALUES (%s)" % (self.table_name,
                                                   ",".join(self.acceptable_group_name),
                                                   ",".join(["?"] * len(self.acceptable_group_name)))
        self.read_log_files(self.log_regx, sql)

    def get_latest_time(self):
        t = self.db.execute("SELECT time_local from %s ORDER BY 1 DESC limit 1" % self.table_name).fetchall()[0][0]
        if not isinstance(t, datetime):
            return db_time2datetime(t)
        return t

    def get_oldest_time(self):
        t = self.db.execute("SELECT time_local from %s ORDER BY 1 ASC limit 1" % self.table_name).fetchall()[0][0]

        if not isinstance(t, datetime):
            return db_time2datetime(t)
        return t

    def read_log_files(self, log_regx, sql):
        # 日志数据处理
        count = 0
        arg_list = []

        for file in fp_gen(self.log_path, pattern=self.log_file_pattern):
            try:
                line = file.readline().strip("\r\n")
                while line:
                    log_tuple = log_regx.search(line)
                    line = file.readline().strip("\r\n")
                    if log_tuple is not None:
                        # 将存在
                        single_line_arg = list(log_tuple.group(group_name) for group_name in log_regx.groupindex if
                                               group_name in self.acceptable_group_name)

                        # 转换日志时间格式为数据库时间格式，方便插入数据库及后续使用数据库时间函数
                        single_line_arg[self.acceptable_group_name.index('time_local')] = log2db_time(
                            log_tuple.group('time_local'), log_str=self.time_local_pattern)

                        arg_list.append(single_line_arg)
                        count += 1
                    if count % 5000 == 0 or line is None or line == "":
                        self.db.execute_many(sql, arg_list)
                        self.output.print_lastLine("Total process: {} logs".format(count))
                        self.db.commit()
                        arg_list.clear()
            except Exception as e:
                raise Exception(e)
            finally:
                file.close()
        self.output.print_info("Total process: {} logs".format(count))
        self.output.print_info("Load log => Done.")

    def update_logs(self, files, log_regx, sql):
        """
        实时更新日志文件，且仅插入非当前已存入数据库时间段内的数据
        用于服务器访问日志实时更新
        :param files: 要更新插入到数据库的日志文件路径
        :param log_regx: 读取日志的正则
        :param sql: 插入sql
        :return:
        """
        count = 0
        arg_list = []
        latest_time = self.get_latest_time()
        for file in files:
            logic_end = False
            for line, is_last in stop_iter(reverse_read_lines(file)):
                try:
                    line = line.strip("\r\n")
                    if line == "":
                        continue
                    log_tuple = log_regx.search(line)
                    current_time = datetime.strptime(log_tuple.group('time_local'), self.time_local_pattern)
                    if current_time <= latest_time:
                        logic_end = True
                    if not logic_end and log_tuple is not None and not logic_end:
                        # 从匹配到的正则分组名中获取需要加入数据库的列名
                        single_line_arg = list(log_tuple.group(group_name) for group_name in log_regx.groupindex if
                                               group_name in self.acceptable_group_name)

                        # 转换日志时间格式为数据库时间格式，方便插入数据库及后续使用数据库时间函数
                        single_line_arg[self.acceptable_group_name.index('time_local')] = log2db_time(
                            log_tuple.group('time_local'), log_str=self.time_local_pattern)

                        arg_list.append(single_line_arg)
                        count += 1
                    if logic_end or count % 5000 == 0 or is_last and count != 0:
                        self.db.execute_many(sql, arg_list)
                        self.db.commit()
                        arg_list.clear()
                except Exception as e:
                    raise UpdateLogThreadException(e)
            # self.output.print_info("Total process: {} logs".format(count))
            # self.output.print_info("Load log => Done.")

    def update_thread_func(self):
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (self.table_name,
                                                   ",".join(self.acceptable_group_name),
                                                   ",".join(["?"] * len(self.acceptable_group_name)))
        while True:
            changes = None
            if self.update_thread_stop_flag:
                return
            try:
                if not self.file_queue.empty():
                    changes = self.file_queue.get(timeout=100)
            except Empty:
                sleep(1)
                continue
            if changes is not None:
                self.update_logs(changes, self.log_regx, sql)
            else:
                sleep(1)

    def get_time_condition(self, when: str, current_flag=False, time_change=False) -> str:
        """
        数据查询时间（WHERE）条件获取
        :param when: ['day','week','month','year']
        :param time_change: 是否改变当前时间(减1单位)
        :param current_flag: 判断是current还是last
        :return: SQL语句约束（WHERE）时间条件
        """
        time_condition_sql = None
        t_w = None
        when = when.lower()

        if when == 'hour':
            t_w = self.time + relativedelta(hours=-1)
            if current_flag:
                time_condition_sql = " DATE(time_local) = '" + self.time.strftime("%Y-%m-%d") \
                                     + "' AND HOUR(time_local) = " + self.time.strftime("%H")

        elif when == 'day':
            t_w = self.time + relativedelta(days=-1)
            if current_flag:
                time_condition_sql = " DATE(time_local) = '" + self.time.strftime("%Y-%m-%d") + "'"

        elif when == 'week':
            t_w = self.time + relativedelta(weeks=-1)
            if current_flag:
                time_condition_sql = " YEAR(time_local) = " + self.time.strftime(
                    "%Y") + " and  WEEK(time_local) =  " + self.time.strftime("%W")

        elif when == 'month':
            t_w = self.time + relativedelta(months=-1)
            if current_flag:
                time_condition_sql = " YEAR(time_local) = " + self.time.strftime(
                    "%Y") + " and MONTH(time_local) = " + self.time.strftime("%m")

        elif when == 'year':
            t_w = self.time + relativedelta(years=-1)
            if current_flag:
                time_condition_sql = " YEAR(time_local) = " + self.time.strftime("%Y")

        if time_change:
            self.time = t_w

        return time_condition_sql + " "

    def get_date_list(self, when: str, d_list: list, time: datetime, d_format_list=None):
        if not isinstance(time, datetime):
            time = db_time2datetime(time)
        if when == 'year':
            d_list.append(time.month)
            if d_format_list is not None:
                d_format_list.append(time.strftime("%Y-%m"))
        elif when == 'month':
            d_list.append(time.day)
            if d_format_list is not None:
                d_format_list.append(time.strftime("%Y-%m-%d"))
        elif when == 'week':
            d_list.append(time.day)
            if d_format_list is not None:
                d_format_list.append(time.strftime("%Y-%m-%d"))
        elif when == 'day':
            d_list.append(time.hour)
            if d_format_list is not None:
                d_format_list.append(time.strftime("%Y-%m-%d %H:00:00"))
        elif when == 'hour':
            d_list.append(time.minute)
            if d_format_list is not None:
                d_format_list.append(time.strftime("%H:%M:00"))

    def check_model_cache_exist(self):
        model_path = os.path.join(self.path, 'analog/cache/model.pkl')
        try:
            if os.path.getsize(model_path) != 0:
                return True
        except FileNotFoundError:
            return False
        return False

    def get_train_progress(self):
        """
        获取训练模型进程的进度
        """
        while True:
            if not self.progress_queue:
                return 0
            if self.progress_queue.empty():
                return 0 if self.train_progress is None else self.train_progress
            progress = self.progress_queue.get_nowait()
            if progress is None or progress == '':
                break
            self.train_progress = 0 if progress is None else progress
        return self.train_progress

    def set_time(self, year=None, month=None, day=None, hour=None, minute=0, second=0) -> datetime:
        year = year if year is not None else self.time.year
        month = month if month is not None else self.time.month
        day = day if day is not None else self.time.day
        hour = hour if hour is not None else self.time.hour
        self.time = datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
        return self.time

    def test(self):
        """
        Test Function for testing model training.
        """
        test_white_path = os.path.join(self.path, "analog/sample_set/test_white_log.txt")
        test_black_path = os.path.join(self.path, "analog/sample_set/test_black_log.txt")
        white_example = []
        black_example = []
        read_by_group(test_white_path, white_example, pattern=self.config.get('log', 'log_content_pattern'))
        read_by_group(test_black_path, black_example, pattern=self.config.get('log', 'log_content_pattern'))
        w_tf_idf_vector = self.tfidfVector.transform(white_example)
        b_tf_idf_vector = self.tfidfVector.transform(black_example)
        y1 = self.model.predict(w_tf_idf_vector)
        TP = y1.tolist().count(1)  # True positive
        FN = y1.tolist().count(-1)  # False Negative
        y2 = self.model.predict(b_tf_idf_vector)
        FP = y2.tolist().count(1)  # False positive
        Precision = 0 if TP == 0 else (TP / (TP + FP))  # Precision
        Recall = 0 if TP == 0 else (TP / (TP + FN))  # Recall
        F1_score = 2 * Precision * Recall / (Precision + Recall)
        test_log_path = os.path.join(self.path, "analog/log")

        with open(os.path.join(test_log_path, "white_test.txt"), "w", encoding='utf-8') as file:
            for i in range(len(white_example)):
                file.write(white_example[i] + " => " + ("正常" if y1[i] == 1 else "恶意") + "请求\n")

        with open(os.path.join(test_log_path, "black_test.txt"), "w", encoding='utf-8') as file:
            for i in range(len(black_example)):
                file.write(black_example[i] + " => " + ("正常" if y2[i] == 1 else "恶意") + "请求\n")
        self.output.print_info("Test Done.")
        self.output.print_info("Precision:%s%%  Recall:%s%%  F1_score:%s  " % (Precision * 100, Recall * 100, F1_score))

    def help(self):
        indent_len = 4
        text_len = 50
        help_text = FormattedText([
            ('class:help_title', '\nUsage:\n'),
            ('class:green', ' ' * indent_len + 'show  '),
            ('class:yellow', '<statistics|analysis|log>  '),
            ('class:yellow', '<IP|requests|UA|url>  '),
            ('class:green', '<current>  '),
            ('class:yellow', '<day|week|month|year|all>  '),
            ('class:yellow', '(top N)\n'),
            ('class:help_title', '\nExample:\n'),
            ('class:yellow', " " * indent_len + 'show statistics requests current day'.ljust(text_len)),
            ('class:white', 'Draw a chart to show statistics of website visit\n'),
            ('class:yellow', " " * indent_len + 'show statistics url last week top 10'.ljust(text_len)),
            ('class:white', 'Draw a chart to show statistics of requests \n'),
            ('class:yellow', " " * indent_len + 'show analysis current day'.ljust(text_len)),
            ('class:white', 'Display log analysis using abnormal detection model.\n'),
            ('class:yellow', " " * indent_len + 'show log current day'.ljust(text_len)),
            ('class:white', 'Display the log in a table.\n'),
            ('class:help_title', '\nMore:\n'),
            ('class:yellow', " " * indent_len + 'train|retrain'.ljust(text_len)),
            ('class:white', 'Train your model\n'),
            ('class:yellow', " " * indent_len + 'get progress'.ljust(text_len)),
            ('class:white', 'Get progress of training model\n'),
            ('class:yellow', " " * indent_len + 'get time|date|offset'.ljust(text_len)),
            ('class:white', 'Display values\n'),
            ('class:yellow', " " * indent_len + 'set date 2019/8/3 '.ljust(text_len)),
            ('class:white', 'Set date\n'),
            ('class:yellow', " " * indent_len + 'set day|month|year|offset N'.ljust(text_len)),
            ('class:white', 'Set values\n'),
            ('class:yellow', " " * indent_len + 'get <values>'.ljust(text_len)),
            ('class:white', 'Get values\n'),
            ('class:help_title', '\nMore information:\n'),
            ('class:blue', " " * indent_len + '<https://analog.testzero-wz.com>\n'),
            ('class:blue', " " * indent_len + '<https://github.com/Testzero-wz>\n'),
        ])
        print_formatted_text(help_text, style=self.style)

    def add_command_help(self):
        indent_len = 4
        help_text = FormattedText([
            ('class:help_title', '\nUsage:\n'),
            ('class:green', ' ' * indent_len + 'add '),
            ('class:yellow', '<hour|day|week|month|year|offset>  '),
            ('class:yellow', 'N\n '),
            ('class:help_title', '\nOr:\n'),
            ('class:green', ' ' * indent_len + 'add '),
            ('class:yellow', '<h|d|w|m|y|o>  '),
            ('class:yellow', 'N\n '),
        ])
        print_formatted_text(help_text, style=self.style)


if __name__ == "__main__":
    pass
