from analog.bin.lib.sql import db
from analog.bin.io.color_output import ColorOutput
from textwrap import wrap
from colorama import Fore, Style
from analog.thirdparty.terminaltables.terminal_io import terminal_size
from analog.thirdparty.terminaltables.other_tables import AnalogTable
from analog.bin.lib.utils import fetch
from configparser import NoOptionError, NoSectionError


class Logger:
    KEY_WORD_IP = 1
    KEY_WORD_DATE = 2

    def __init__(self, database: db,
                 output: ColorOutput,
                 section_name_log="Log",
                 ipdb=None,
                 controller=None,
                 tfidfvector=None,
                 config=None,
                 model=None
                 ):
        self.db = database
        self.ip_db = ipdb
        self.config = config
        self.controller = controller
        self.tfidfvector = tfidfvector
        self.model = model
        self.offset = 0
        self.output = output
        self.ip = None
        self.query_cache = []
        self.show_num = 6
        self.total_len = 0

        self.section_name_log = section_name_log
        self.logs_per_query = int(self.config.get(self.section_name_log, 'logs_per_query'))
        self.N = self.logs_per_query
        self.freeze = False
        self.MODE = self.KEY_WORD_IP

        self.when_buff = None

    def add_offset(self, N):
        self.set_offset(self.offset + N)

    def set_ip(self, ip: str):
        self.ip = ip
        self.output.print_info(ip)

    def set_offset(self, offset: int):
        self.offset = self.total_len - self.show_num if offset > self.total_len else offset
        self.offset = self.offset if self.offset > 0 else 0

    def set_mode(self, mode: str):
        mode = mode.lower()
        if mode == "date":
            self.MODE = self.KEY_WORD_DATE
        elif mode == 'ip':
            self.MODE = self.KEY_WORD_IP

    def show_log(self, increase=False, decrease=False, when=None, current_flag=True):
        assert ~(increase and decrease)
        if increase:
            self.add_offset(self.show_num)
        else:
            self.add_offset(-self.show_num)
        offset = self.offset
        if len(self.query_cache) == 0 or offset >= self.N:
            if offset >= self.N:
                self.N += self.logs_per_query
            cursor = None
            if self.MODE == self.KEY_WORD_IP:
                cursor = self.db.execute(
                    """
                    SELECT 
                    time_local,
                    status,
                    request,
                    body_bytes_sent,
                    http_referer,
                    http_user_agent,
                    remote_addr
                    FROM `%s` WHERE
                    remote_addr = ? """ % self.controller.table_name + "ORDER BY time_local DESC " +
                    "LIMIT " + str(self.offset) + "," + str(self.logs_per_query),
                    self.ip
                )
            elif self.MODE == self.KEY_WORD_DATE:
                if when:
                    self.when_buff = when
                cursor = self.db.execute(
                    """
                    SELECT 
                    time_local,
                    status,
                    request,
                    body_bytes_sent,
                    http_referer,
                    http_user_agent,
                    remote_addr
                    FROM `%s` WHERE
                    """ % self.controller.table_name + self.controller.get_time_condition(self.when_buff,
                                                                                          time_change=False,
                                                                                          current_flag=current_flag) +
                    "ORDER BY time_local " +
                    "LIMIT " + str(self.offset) + "," + str(self.logs_per_query)
                )

            res = list(cursor.fetchall())
            if len(res) == 0:
                self.output.print_info("No more logs.")
                return False
            if self.model:
                predict_vector = self.tfidfvector.transform(fetch(res, 2))
                predict_res = self.model.predict(predict_vector)
                for i in range(len(res)):
                    res[i] += (predict_res[i],)
            self.query_cache.extend(res)
            self.total_len += len(res)
            if len(res) == 0 or len(res) != self.logs_per_query:
                self.freeze = True

        data = []

        res = self.query_cache[self.offset:self.offset + self.show_num]

        t = self.offset + 1
        for log_item in res:
            list_temp = []
            str_temp = "{:^6s}".format("Ord:") + "│Status: " + self.get_status_color_font(log_item[1]) \
                       + '\n' + Fore.YELLOW + "{:^6d}".format(t) + Fore.RESET + "│Length: " + str(log_item[3]) \
                       + "\n──────┴─────────────\n" + str(log_item[0])
            list_temp.append(str_temp)
            if self.MODE == self.KEY_WORD_DATE or self.MODE == self.KEY_WORD_IP:
                geolocation_list = self.ip_db.find(log_item[6])
                if geolocation_list[0] != '中国':
                    geolocation_str = geolocation_list[0]
                else:
                    geolocation_str = "".join(geolocation_list)
                ip_str = log_item[6] + "\n" + geolocation_str
                if self.model:
                    ip_str += "\n" + "─" * (ip_str.find('\n') if ip_str.find('\n') != -1 else 1) + "\n" + \
                              (Fore.LIGHTBLUE_EX + "正常请求" if log_item[7] == 1 else Fore.LIGHTRED_EX + "恶意请求") + \
                              Fore.RESET
                list_temp.append(ip_str)
            column_number = len(list_temp) + 3 + 1
            current_len = 0
            for i in list_temp:
                current_len += i.find('\n') if i.find('\n') != -1 else 1
            current_len += column_number
            left_size = terminal_size()[0] - current_len - 4
            url_width = referer_width = other_width = left_size // 3
            list_temp.append('\n'.join(wrap(log_item[2], url_width)))
            list_temp.append('\n'.join(wrap(log_item[4], referer_width)))
            list_temp.append('\n'.join(wrap(log_item[5], other_width)))
            data.append(list_temp)
            t += 1

        table = AnalogTable(data)

        if self.MODE == self.KEY_WORD_IP:
            self.output.print_split_line(message="Log of IP {} {}".format(self.ip, "".join(self.ip_db.find(self.ip))))
        table.inner_row_border = True
        print(Style.RESET_ALL + table.table)
        return True

    @staticmethod
    def get_status_color_font(status: int):
        color = Fore.LIGHTMAGENTA_EX
        if 100 <= status < 200:
            color = Fore.LIGHTWHITE_EX
        elif 200 <= status < 300:
            color = Fore.LIGHTYELLOW_EX
        elif 300 <= status < 400:
            color = Fore.LIGHTBLUE_EX
        elif 400 <= status < 500:
            color = Fore.LIGHTRED_EX

        return color + str(status) + Fore.RESET

    def clear(self):
        self.total_len = 0
        self.offset = 0
        self.freeze = False
        self.query_cache.clear()
        self.ip = None
