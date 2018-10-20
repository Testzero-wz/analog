# coding:utf-8

from analog.bin.lib.sql import db
from analog.bin.io.color_output import ColorOutput
from analog.bin.exception.Exceptions import *
from analog.bin.machine_learning.train import *
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.filters import Condition
from dateutil.relativedelta import relativedelta
import os
import configparser
import re
from datetime import datetime
from prompt_toolkit.formatted_text import FormattedText, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings, ConditionalKeyBindings
from analog.bin.io.completer import AnalogCompleter
from analog.bin.lib.statistics import Statistics
from analog.bin.lib.log import Logger
import ipdb
import multiprocessing
from multiprocessing import Manager
from analog.bin.machine_learning.TfidfVector import TfidfVector
from analog.bin.check.check import check_txt
from analog.bin.lib.analysis import Analyser
import pickle


NORMAL_MODE = 1
LOGGING_MODE = 2

from time import sleep


class Controller:
    analog_completer = AnalogCompleter(
            [
                ['show', 'set', 'train', 'clear', 'help', 'exit'],
                ['statistics', 'analysis', 'log', 'progress'],
                ['requests', 'IP', 'UA', 'url'],
                ['current', 'last'],
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


    def __init__(self, path=None):

        self.path = path
        self.config_path = os.path.join(self.path, "config.ini")
        self.time = datetime.now()
        self.output = ColorOutput()
        self.output.print_banner("AnaLog")

        if os.path.exists(self.config_path):
            self.config = configparser.ConfigParser()
            self.config.read(self.config_path)
        else:
            raise DatabaseConfigError

        self.log_path = self.config.get('log', 'path')

        self.db = db(self.config)
        self.section_name_database = "Database"
        self.ip_db = ipdb.Reader(os.path.join(self.path, "analog/ipdb/ip.ipdb"))

        # 数据库初始化
        if self.config.get(self.section_name_database, 'initial') != '1':
            self.init_database()
            self.config.set(self.section_name_database, 'initial', '1')

            self.init_table()
            self.config.write(open(self.config_path, "w"))
        else:
            try:
                self.db.connect_db()
            except Exception as e:
                self.output.print_error(
                        "Connect DB failed. Please check your config file or make sure DB server is running.")
                self.output.print_info("Bye~")
                exit(0)
            self.output.print_info(
                    "Log had been loaded before.Type " + self.output.Fore.BLUE + "reload" + self.output.Style.RESET_ALL + self.output.Fore.LIGHTYELLOW_EX + " to flush")

        self.statistic = Statistics(database=self.db, output=self.output, ipdb=self.ip_db, controller=self)

        self.session = PromptSession()
        self.mode = NORMAL_MODE
        self.key_bindings = None

        # TF-IDF向量填充词料库
        tfidf_exist_flag = False
        self.tfidfVector = None
        try:
            self.tfidfVector = TfidfVector()
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
        self.queue = None
        self.train_progress = 0

        # 模型缓存载入
        if tfidf_exist_flag is False:
            print_formatted_text(
                    HTML('<yellow>Cause of you lack of TF-IDF corpus'
                         '(<red>analog/sample_set/train.txt</red>), We can\'t calculate TF-IDF value'
                         'of each log item and can\'t use train model also</yellow>'),
                    style=self.style)
        elif self.check_model_cache_exist():
            print_formatted_text(
                    HTML('<yellow>Detection model cache file exist.\nLoad model from it.\nYou can type '
                         '<blue>retrain</blue> to train a new model.</yellow>'),
                    style=self.style)
            self.load_model()

        else:
            try:
                if self.train() is False:
                    print_formatted_text(
                            HTML('<yellow>Train Failed! Cause of lack of train sample. '
                                 '\nVisit <blue>https://www.wzsite.cn</blue> for help.</yellow>'),
                            style=self.style)
            except Exception as e:
                raise e

        self.logger = Logger(database=self.db, output=self.output, ipdb=self.ip_db,
                             controller=self, tfidfvector=self.tfidfVector, model=self.model)
        self.analyser = Analyser(database=self.db, ipdb=self.ip_db,
                                 controller=self, tfidfvector=self.tfidfVector, model=self.model)


    def mainloop(self):
        self.key_bindings = KeyBindings()


        @Condition
        def is_logging_mode():
            return self.mode == LOGGING_MODE


        @self.key_bindings.add('up')
        def _(event):
            self.clear_screen()
            self.logger.show_log(decrease=True)
            print_formatted_text(
                    HTML('<yellow>Press <blue>↑</blue> or <blue>↓</blue> to turn pages or '
                         '<blue>Esc</blue> to quit log mode</yellow>'),
                    style=self.style)
            print_formatted_text(FormattedText(self.analog_prompt), end="")


        @self.key_bindings.add('down')
        def _(event):
            self.clear_screen()
            self.logger.show_log(increase=True)
            print_formatted_text(
                    HTML('<yellow>Press <blue>↑</blue> or <blue>↓</blue> to turn pages or '
                         '<blue>Esc</blue> to quit log mode</yellow>'),
                    style=self.style)
            print_formatted_text(FormattedText(self.analog_prompt), end="")


        @self.key_bindings.add('escape')
        def _(event):
            # self.clear_screen()
            self.mode = NORMAL_MODE
            self.logger.clear()
            print_formatted_text(
                    HTML('<yellow>\nBack to normal mode.\nanalog> </yellow>'), style=self.style, end="")


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
            except CommandFormatError:
                self.output.print_error(
                        "Unknown command: {}. Type \"help\" for help.".format(
                                text if text else "(Failed to read command)"))


    def train(self):
        if not self.check_train_txt():
            return False
        model_train = Train(self.path)
        self.queue = multiprocessing.Manager().Queue()
        pool = multiprocessing.Pool(1)
        pool.apply_async(model_train.get_model, args=(self.queue,), callback=self.load_model)
        pool.close()
        print_formatted_text(
                HTML('<yellow>Start the model training process.'
                     '\nYou can type <blue>train progress</blue> to get the progress of training.</yellow>'),
                style=self.style)


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
                HTML('\n<blue>Training task complete! '
                     'Try to type command <white>show analysis</white> to show'
                     'abnormal analysis!</blue>'), style=self.style)
        self.logger.model = self.model


    def load_model(self, *args):
        with open(os.path.join(self.path, r'analog/cache/model.pkl'), 'rb') as file:
            self.model = pickle.load(file)


    def help(self):
        help_text = FormattedText([
            ('class:help_title', 'Usage:\n'),
            ('class:green', ' ' * 4 + 'show  '),
            ('class:yellow', '<statistics|analysis|log>  '),
            ('class:yellow', '<IP|requests|UA|url>  '),
            ('class:green', '<current|last>  '),
            ('class:yellow', '<day|week|month|year|all>  '),
            ('class:yellow', '(top N)\n'),
            ('class:help_title', 'Example:\n'),
            ('class:yellow', " " * 4 + 'show statistics requests current day'.ljust(50)),
            ('class:white', 'Draw a chart to show statistics of website visit\n'),
            ('class:yellow', " " * 4 + 'show statistics url last week top 10'.ljust(50)),
            ('class:white', 'Draw a chart to show statistics of requests \n'),
            ('class:yellow', " " * 4 + 'show analysis of current day'.ljust(50)),
            ('class:white', 'Display log analysis using abnormal detection model.\n'),
            ('class:yellow', " " * 4 + 'show log of current day'.ljust(50)),
            ('class:white', 'Display the log in a table.\n'),
            ('class:help_title', 'More:\n'),
            ('class:yellow', " " * 4 + 'train|retrain'.ljust(50)),
            ('class:white', 'Train a model\n'),
            ('class:yellow', " " * 4 + 'train progress'.ljust(50)),
            ('class:white', 'Get progress of training model\n'),
            ('class:yellow', " " * 4 + 'set time|day|month|year|offset N'.ljust(50)),
            ('class:white', 'Set values\n'),
            ('class:help_title', 'More information:\n'),
            ('class:blue', " " * 4 + '<https://www.wzstie.cn>\n'),
            ('class:blue', " " * 4 + '<https://github.com/Testzero-wz>\n'),
        ])
        print_formatted_text(help_text, style=self.style)


    def get_train_progress(self):
        """
        获取训练模型进程的进度
        :return:
        """
        while True:
            try:
                if not self.queue:
                    return
                progress = self.queue.get_nowait()
                if progress is None or progress == '':
                    break
            except Exception:
                break
            self.train_progress = progress
        return self.train_progress


    def set_time(self, year=None, month=None, day=None, hour=None, minute=0, second=0) -> datetime:
        year = year if year is not None else self.time.year
        month = month if month is not None else self.time.month
        day = day if day is not None else self.time.day
        hour = hour if hour is not None else self.time.hour
        self.time = datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
        return self.time


    def command_parser(self, command: str):
        """
        命令解析
        """
        command = command.lower()
        command = command.split()
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
                    if command[2] == 'of' and command[3] == 'current':
                        self.analyser.show_analysis(command[4])
                elif command[1] == 'ip':
                    self.output.print_info("-".join(self.statistic.ip_geolocation(command[2])))

                elif command[1] == 'log':
                    flag = False
                    if command[3] == 'ip':
                        self.logger.set_mode('ip')
                        self.logger.set_ip(command[4])
                        flag = self.logger.show_log()

                    elif command[3] in ['current', 'last']:
                        self.logger.set_mode('date')
                        flag = self.logger.show_log(when=command[4],
                                                    current_flag=True if command[3] == 'current' else False)

                    self.mode = LOGGING_MODE if flag else NORMAL_MODE

            elif c == 'set':

                if command[1] == 'time':
                    t = datetime.strptime(command[2], "%Y/%m/%d:%H")
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
            elif c == 'train' or c == 'retrain':
                if len(command) == 1:
                    self.train()
                elif command[-1] == "progress":
                    progress = float(self.get_train_progress()) * 100
                    if progress == 100:
                        self.train_complete()
                    else:
                        self.output.print_info(
                                "Now train progress is {:0.2f}%".format(progress))
            elif c == 'clear':
                self.clear_screen()
            elif c == 'help':
                self.help()
            elif c == 'exit':
                print_formatted_text(FormattedText([('class:yellow', '[*] Bye~')]), style=self.style)
                exit(0)
            elif c == 'get':
                if command[1] == 'model' and command[2] == 'parameter':
                    if self.model:
                        params = self.model.get_params('nu')
                        print_formatted_text(FormattedText([('class:yellow', 'nu: {}'.format(params.get('nu')))]),
                                             style=self.style)
                        print_formatted_text(
                                FormattedText([('class:yellow', 'gamma: {}'.format(params.get('gamma')))]),
                                style=self.style)
                    else:
                        self.output.print_info("No model has been loaded.")
            else:
                raise CommandFormatError
        except Exception as e:
            raise CommandFormatError
            # import traceback
            # traceback.print_exc()
            # raise Exception(e)


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

        # Create Table: access_record
        sql = """
                 CREATE TABLE IF NOT EXISTS access_count (
                 ip  CHAR(15) NOT NULL PRIMARY KEY,
                 total_access  INT DEFAULT 0,
                 year_access INT DEFAULT 0,  
                 month_access INT DEFAULT 0,
                 week_access INT DEFAULT 0, 
                 day_access INT DEFAULT 0);
                 """
        cursor.execute(sql)

        # Create Table: weblog
        sql = """CREATE TABLE IF NOT EXISTS weblog (
                             remote_addr  CHAR(15) NOT NULL ,
                             remote_user  VARCHAR(20),
                             time DATETIME DEFAULT '1970-01-01 00:00:00',
                             request TEXT DEFAULT NULL,
                             status  SMALLINT  UNSIGNED DEFAULT 0, 
                             body_bytes_sent INT DEFAULT 0,
                             http_referer TEXT DEFAULT NULL,
                             http_user_agent TEXT DEFAULT NULL);
                             """
        cursor.execute(sql)
        conn.commit()
        conn.close()
        self.output.print_info("Initial database => Done.")


    def init_table(self):
        """
        数据库表单载入初始化
        将日志载入数据库中
        """
        count = 0
        arg_list = []
        log_Pattern = r'^(?P<remote_addr>.*?) - (?P<remote_user>.*) \[(?P<time_local>.*?) \+[0-9]+?\] "(?P<request>.*?)" ' \
                      '(?P<status>.*?) (?P<body_bytes_sent>.*?) "(?P<http_referer>.*?)" "(?P<http_user_agent>.*?)"$'

        sql = "INSERT weblog(" \
              "remote_addr,remote_user,time,request,status," \
              "body_bytes_sent,http_referer,http_user_agent)  " \
              "VALUES " \
              "(%s,%s,%s,%s,%s,%s,%s,%s)"

        log_regx = re.compile(log_Pattern)
        with open(self.log_path, "r") as file:
            line = file.readline().strip("\r\n")
            while line:
                log_tuple = log_regx.search(line)
                line = file.readline().strip("\r\n")
                if log_tuple is not None:
                    # continue
                    t = datetime.strptime(log_tuple.group('time_local'), "%d/%b/%Y:%H:%M:%S")
                    arg_list.append(
                            (
                                log_tuple.group('remote_addr'),
                                log_tuple.group('remote_user'),
                                t.strftime("%Y/%m/%d %H:%M:%S"),
                                log_tuple.group('request'),
                                int(log_tuple.group('status')),
                                int(log_tuple.group('body_bytes_sent')),
                                log_tuple.group('http_referer'),
                                log_tuple.group('http_user_agent')
                            )

                    )
                    count += 1
                if count % 5000 == 0 or line is None or line == "":
                    self.db.execute_many(sql, arg_list)
                    self.output.print_lastLine("Total process: {} logs".format(count))
                    self.db.commit()
                    arg_list.clear()
        self.output.print_info("Total process: {} logs".format(count))
        self.output.print_info("Load log => Done.")


    def get_time_condition(self, when: str, time_change=False, current_flag=False) -> str:
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
                time_condition_sql = " DATE(time) = '" + self.time.strftime("%Y-%m-%d") \
                                     + "' AND HOUR(time) = '" + self.time.strftime("%H") + "'"
            else:
                time_condition_sql = " time BETWEEN ('" + self.time.strftime("%Y-%m-%d %H:%M:00") \
                                     + "' - INTERVAL 1 HOUR ) and '" + self.time.strftime(
                        "%Y-%m-%d %H:%M:00") + "'"

        elif when == 'day':
            t_w = self.time + relativedelta(days=-1)
            if current_flag:
                time_condition_sql = " DATE(time) = '" + self.time.strftime("%Y-%m-%d") + "'"
            else:
                time_condition_sql = " time BETWEEN ('" + self.time.strftime("%Y-%m-%d %H:00:00") \
                                     + "' - INTERVAL 1 DAY ) and '" + self.time.strftime(
                        "%Y-%m-%d %H:00:00") + "'"
        elif when == 'week':
            t_w = self.time + relativedelta(weeks=-1)
            if current_flag:
                time_condition_sql = " YEAR(time) = '" + self.time.strftime(
                        "%Y") + "'and  WEEK(time) = '" + self.time.strftime("%W") + "'"
            else:
                time_condition_sql = " time BETWEEN ('" + self.time.strftime("%Y-%m-%d") \
                                     + "' - INTERVAL 1 WEEK ) and '" + self.time.strftime("%Y-%m-%d") + "'"
        elif when == 'month':
            t_w = self.time + relativedelta(months=-1)
            if current_flag:
                time_condition_sql = " YEAR(time) = '" + self.time.strftime(
                        "%Y") + "'and MONTH(time) = '" + self.time.strftime("%m") + "'"
            else:
                time_condition_sql = " time BETWEEN ('" + self.time.strftime("%Y-%m-%d") \
                                     + "' - INTERVAL 1 MONTH ) and '" + self.time.strftime("%Y-%m-%d") + "'"
        elif when == 'year':
            t_w = self.time + relativedelta(years=-1)
            if current_flag:
                time_condition_sql = " YEAR(time) = '" + self.time.strftime("%Y") + "'"
            else:
                time_condition_sql = " time BETWEEN ('" + self.time.strftime("%Y-%m-%d") \
                                     + "' - INTERVAL 1 YEAR ) and '" + self.time.strftime("%Y-%m-%d") + "'"
        if time_change:
            self.time = t_w

        return time_condition_sql


    def get_date_list(self, when: str, d_list: list, time: datetime, d_format_list=None):
        t = time
        if when == 'year':
            d_list.append(t.month)
            if d_format_list is not None:
                d_format_list.append(t.strftime("%Y-%m"))
        elif when == 'month':
            d_list.append(t.day)
            if d_format_list is not None:
                d_format_list.append(t.strftime("%Y-%m-%d"))
        elif when == 'week':
            d_list.append(t.day)
            if d_format_list is not None:
                d_format_list.append(t.strftime("%Y-%m-%d"))
        elif when == 'day':
            d_list.append(t.hour)
            if d_format_list is not None:
                d_format_list.append(t.strftime("%Y-%m-%d %H:00:00"))
        elif when == 'hour':
            d_list.append(t.minute)
            if d_format_list is not None:
                d_format_list.append(t.strftime("%H:%M:00"))


    def check_model_cache_exist(self):
        model_path = os.path.join(self.path, 'analog/cache/model.pkl')
        try:
            if os.path.getsize(model_path) != 0:
                return True
        except FileNotFoundError:
            return False
        return False


if __name__ == "__main__":
    # c = Controller()
    pass
