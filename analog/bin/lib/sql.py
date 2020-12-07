from analog.bin.exception.Exceptions import *
from os import path
import os
from datetime import datetime

Connection = None


class db:

    def __init__(self, config, root_path):

        self.section_name = 'Database'
        self.connect = None
        self.config = config
        self.database_name = self.config.get(self.section_name, 'database')
        self.root_path = root_path
        self.db_type = self.config.get(self.section_name, 'db_type')
        if self.db_type == "mysql":
            from pymysql import connect
        else:
            from sqlite3 import connect
            self.database_path = path.join(self.root_path, "analog/sqlitedb")
            self.database_name = path.join(self.database_path, self.database_name + ".db")
        global Connection
        Connection = connect

    def connect_db(self):
        if Connection is None:
            raise ImportError("Database Lib import error.")
        if self.db_type == 'mysql':
            self.connect = Connection(host=self.config.get(self.section_name, 'host'),
                                      port=int(self.config.get(self.section_name, 'port')),
                                      user=self.config.get(self.section_name, 'user'),
                                      password=self.config.get(self.section_name, 'password'),
                                      database=self.config.get(self.section_name, 'database'),
                                      charset=self.config.get(self.section_name, 'charset'))
        else:
            self.connect_sqlite_db()

        return self.connect

    def connect_sqlite_db(self):
        if not os.path.exists(self.database_path):
            os.mkdir(self.database_path)
        self.connect = Connection(self.database_name)
        self.register_sqlite_date_function()

    def register_sqlite_date_function(self):
        func_names = {"YEAR": self.sqlite_year,
                      "MONTH": self.sqlite_month,
                      "WEEK": self.sqlite_week,
                      "DAY": self.sqlite_day,
                      "HOUR": self.sqlite_hour,
                      "MINUTE": self.sqlite_minute,
                      "DATE": self.sqlite_date,
                      "DAYOFMONTH": self.sqlite_day}
        for func_name, func in func_names.items():
            self.connect.create_function(func_name, 1, func)

    def connect_without_db(self):
        self.connect = Connection(host=self.config.get(self.section_name, 'host'),
                                  port=int(self.config.get(self.section_name, 'port')),
                                  user=self.config.get(self.section_name, 'user'),
                                  password=self.config.get(self.section_name, 'password'),
                                  charset=self.config.get(self.section_name, 'charset'))
        return self.connect

    def close(self):
        if self.connect:
            self.connect.close()

    def execute_many(self, sql, args):
        try:
            cursor = self.connect.cursor()
            cursor.executemany(sql, args)
        except Exception as e:
            self.connect_db()
            cursor = self.connect.cursor()
            cursor.executemany(sql, args)
        return cursor

    def execute(self, sql: str, args: object = tuple()):
        try:
            cursor = self.connect.cursor()
            cursor.execute(sql, args)
        except Exception as e:
            self.connect_db()
            cursor = self.connect.cursor()
            cursor.execute(sql, args)
        return cursor

    def commit(self):
        self.connect.commit()

    def update(self, *args):
        cursor = self.connect.cursor()
        try:
            arguments = {"table_name": args[0], "values": "",
                         "conditions": "WHERE %s" % args[2] if len(args) > 2 else ""}
            flag = False
            string = ""
            if isinstance(args[1], dict):
                for item in args[1].items():
                    if flag:
                        string += ","

                    string += "{0} = {1}".format(item[0], item[1])

                    if flag is False:
                        flag = True

            arguments['values'] = string
            cursor.execute("UPDATE :table_name SET :values :conditions", arguments)
            self.connect.commit()
        except Exception:
            return False

    def create_db(self):
        _connection = None
        try:
            _connection = None
            if self.db_type == 'mysql':
                _connection = self.connect_without_db()
                cursor = _connection.cursor()
                cursor.execute('create database if not exists {}'.format(self.database_name))
                _connection.commit()
        except Exception as e:
            raise DatabaseException("Can't create database, make sure your config are correct!")
        finally:
            if _connection:
                _connection.close()
        return True

    @staticmethod
    def sqlite_date(time_str):
        return datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S").strftime("%Y-%m-%d")

    @staticmethod
    def sqlite_year(time_str):
        return datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S").year

    @staticmethod
    def sqlite_month(time_str):
        return datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S").month

    @staticmethod
    def sqlite_week(time_str):
        return int(datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S").strftime("%U"))

    @staticmethod
    def sqlite_day(time_str):
        return datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S").day

    @staticmethod
    def sqlite_hour(time_str):
        return datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S").hour

    @staticmethod
    def sqlite_minute(time_str):
        return datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S").minute


if __name__ == "__main__":
    pass
