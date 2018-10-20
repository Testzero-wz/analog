from analog.bin.lib.sql import db
from analog.bin.io.chart import Histogram
from analog.bin.exception.Exceptions import *


def requests_num_decorator(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        self.output.print_info("Now time is {}".format(self.controller.time.strftime("%Y/%m/%d:%H:00")))
        self.output.print_info(
                "You can type command: " + self.output.Fore.LIGHTBLUE_EX + "set <hour|day|mouth|year> <num>" + \
                self.output.Fore.LIGHTYELLOW_EX + "  or  " + self.output.Fore.LIGHTBLUE_EX + "set time 2018/8/8:10 " + \
                self.output.Fore.LIGHTYELLOW_EX + "to change current time."
        )


    return wrapper


class Statistics:

    def __init__(self, database: db,
                 time=None,
                 output=None,
                 ipdb=None,
                 controller=None
                 ):
        # self.controller.time = time if time else datetime.now()
        self.db = database
        self.ip_db = ipdb
        self.output = output
        self.controller = controller


    def top_n(self, query: str, when: str, current_flag=False, N=10):
        date_condition = self.controller.get_time_condition(when, current_flag=current_flag)
        sub_title = self.get_title(when)
        query = query.lower()
        if query == 'ip':
            # ================================================ IP统计 ===================================================
            column_name = "remote_addr"
            self.output.print_split_line(message="IP Statistics - {}".format(sub_title))
            __title = "IP"
        elif query == 'ua':
            # ================================================ UA统计 ==================================================
            self.output.print_split_line(message="User-Agent Statistics- {}".format(sub_title))
            column_name = "http_user_agent"
            __title = "User-Agent"
        elif query == 'url':
            # ================================================ URL统计 =================================================
            column_name = "request"
            __title = "Request-URL"
        elif query == 'status':
            # =============================================== Status统计 ===============================================
            column_name = "status"
            self.output.print_split_line(message="Status Statistics- {}".format(sub_title))
            __title = "Status"
        else:
            raise CommandFormatError

        cursor = self.db.execute(
                "SELECT " + column_name + ",COUNT(*) FROM weblog WHERE" + date_condition + """
                                                GROUP BY 1
                                                ORDER BY 2 DESC
                                                LIMIT 0,""" + str(N)
        )
        res = cursor.fetchall()
        if res == ():
            self.output.print_info("No result", symbol="-")
            return
        if query == 'ip':
            title = "{:<12s}{:<12s}{:<20s}{}".format("Ordinal", "Count", __title, "Geolocation")
        else:
            title = "{:<12s}{:<12s}{:<20s}".format("Ordinal", "Count", __title)

        self.output.print_info(message=title)
        t = 1
        for i in res:
            self.output.print_info("{:<12s}{:<12d}{:<20s}".format("{:^7d}".format(t), i[1], i[0]) + \
                                   ("-".join(self.ip_db.find(i[0])) if query == 'ip' else ""), symbol="+")
            t += 1


    @requests_num_decorator
    def requests_num(self, when: str, current_flag=False, time_change=False):
        # ================================================ 请求数统计 ==============================================
        t = self.controller.time
        when = when.lower()
        temp_list = [0] * 61
        sub_title = self.get_title(when)
        date_condition = self.controller.get_time_condition(when, current_flag=current_flag, time_change=time_change)
        if when == 'hour':
            column_name = "MINUTE(time)"
        elif when == 'day':
            column_name = "HOUR(time)"
        elif when == 'week':
            column_name = "DAYOFMONTH(time)"
        elif when == 'month':
            column_name = "DAYOFMONTH(time)"
        elif when == 'year':
            column_name = "MONTH(time)"
        else:
            raise CommandFormatError

        sql = "SELECT " + column_name + ",COUNT(*),time FROM weblog WHERE " + date_condition + "GROUP BY 1 ORDER BY 3"
        cursor = self.db.execute(sql)
        res = cursor.fetchall()
        if res == ():
            self.output.print_info("No result", symbol="-")
            return
        self.output.print_split_line(message="Number Of Requests - {}".format(sub_title))
        date_list = []
        date_format_list = []
        for i in res:
            temp_list[i[0]] = i[1]
            self.controller.get_date_list(when, date_list, i[2], d_format_list=date_format_list)

        chart = Histogram(
                list(map(lambda x, y: (x, y), date_format_list, [temp_list[i] for i in date_list])))
        chart.draw()


    def top(self, value, when: str):
        pass


    def get_title(self, when: str) -> str:
        if when == 'day':
            title = "24 Hours"
        elif when == 'week':
            title = "Week"
        elif when == 'month':
            title = "Month"
        elif when == 'year':
            title = "Year"
        elif when == 'hour':
            title = "Hour"
        else:
            title = "Total"
        return title


    def ip_geolocation(self, ip: str) -> list:
        return self.ip_db.find(ip)
