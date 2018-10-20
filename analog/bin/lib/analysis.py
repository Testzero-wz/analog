from analog.bin.lib.sql import db
from analog.bin.io.color_output import ColorOutput
from analog.thirdparty.terminaltables.terminal_io import terminal_size
from analog.thirdparty.terminaltables.other_tables import AnalogTable
from colorama import Fore, Style
from analog.bin.machine_learning.TfidfVector import TfidfVector
from collections import Counter


class Analyser:
    def __init__(self,
                 controller=None,
                 tfidfvector=None,
                 model=None,
                 database=None,
                 ipdb=None
                 ):
        self.db = database
        self.ip_db = ipdb
        self.tfidfvector = tfidfvector
        self.model = model
        self.controller = controller


    def show_analysis(self, when: str):
        cursor = self.db.execute(
                """
                SELECT 
                COUNT(*)
                FROM `weblog` WHERE""" +
                self.controller.get_time_condition(when, time_change=False, current_flag=True)
        )
        count = cursor.fetchall()[0][0]

        if count > 50000:
            self.controller.output.print_info(
                    "Number of log items is too large({}). It will take a while.".format(count))
        elif count == 0:
            self.controller.output.print_info("No log.")
            return
        cursor = self.db.execute(
                """
                SELECT 
                remote_addr,
                request
                FROM `weblog` WHERE""" +
                self.controller.get_time_condition(when, time_change=False, current_flag=True)
        )
        res = list(cursor.fetchall())
        tf_idf_vector = self.tfidfvector.transform(list(self.__fetch(res, 1, TfidfVector.get_url)))

        y = self.model.predict(tf_idf_vector)
        # 去除正常请求，只留异常请求
        for i in range(0, len(res))[::-1]:
            if y[i] == 1:
                del res[i]

        # ========================================== 恶意IP统计 ==========================================
        self.controller.output.print_split_line(message="Abnormal Access IP ")
        ip_counter = Counter(self.__fetch(res, 0))
        data = []
        data.append(("恶意IP", "定位", "恶意请求占比"))
        for item in ip_counter.most_common(10):
            geolocation_list = self.ip_db.find(item[0])
            if geolocation_list[0] != '中国':
                geolocation_str = geolocation_list[0]
            else:
                geolocation_str = "".join(geolocation_list)
            data.append((item[0], geolocation_str, "{:4.2f}%".format(item[1] / len(res) * 100)))
        ip_table = AnalogTable(data)
        print(Style.RESET_ALL + ip_table.table)

        # ========================================== 恶意请求统计 ==========================================
        self.controller.output.print_split_line(message="Abnormal Requests ")
        request_counter = Counter(self.__fetch(res, 1))
        data.clear()
        data.append(("序号", "请求次数", "恶意请求"))
        ordinary = 1
        for item in request_counter.most_common(10):
            data.append((ordinary, item[1], item[0]))
            ordinary += 1
        request_table = AnalogTable(data)
        print(Style.RESET_ALL + request_table.table)

        # ========================================== 恶意IP定位统计 ==========================================
        self.controller.output.print_split_line(message="Geolocation Of Abnormal Requests ")
        geo_list = []
        for ip in self.__fetch(res, 0):
            geolocation_list = self.ip_db.find(ip)
            if geolocation_list[0] != '中国':
                geolocation_str = geolocation_list[0]
            else:
                geolocation_str = "".join(geolocation_list)
            geo_list.append(geolocation_str)
        geo_counter = Counter(geo_list)
        data.clear()
        data.append(("序号", "定位", "恶意请求次数", "地区百分比"))
        ordinary = 1
        for item in geo_counter.most_common(10):
            data.append((ordinary, item[0], item[1], "{:4.2f}%".format(item[1] / len(res) * 100)))
            ordinary += 1
        geo_table = AnalogTable(data)
        print(Style.RESET_ALL + geo_table.table)

        # ========================================== 恶意请求占比 ==========================================
        self.controller.output.print_split_line(message="Proportion Of Abnormal Requests ")
        data_1 = list()
        data_1.append(("恶意请求", "正常请求"))
        evil_percent = len(res) / count * 100
        data_1.append((Fore.LIGHTRED_EX + "{:4.2f}%".format(evil_percent) + Fore.RESET,
                       Fore.LIGHTYELLOW_EX + "{:4.2f}%".format(100 - evil_percent) + Fore.RESET))
        request_percent_table = AnalogTable(data_1)
        print(Style.RESET_ALL + request_percent_table.table)


    @staticmethod
    def __fetch(res: list, index: int, proc=None):

        for item in res:
            if proc:
                yield proc(item[index])
            else:
                yield item[index]
