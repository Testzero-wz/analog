import pymysql
from analog.bin.exception.Exceptions import *
from pymysql.cursors import Cursor
from datetime import datetime
from dateutil.relativedelta import relativedelta


class db:

    def __init__(self, config, controller=None):

        self.section_name = 'Database'
        self.database_name = 'WebLog_Analysis'
        self.connect = None
        self.config = config
        self.controller = controller


    def connect_db(self):

        self.connect = pymysql.connect(host=self.config.get(self.section_name, 'host'),
                                       port=int(self.config.get(self.section_name, 'port')),
                                       user=self.config.get(self.section_name, 'user'),
                                       password=self.config.get(self.section_name, 'password'),
                                       database=self.config.get(self.section_name, 'database'),
                                       charset=self.config.get(self.section_name, 'charset'))
        return self.connect


    def close(self):
        if self.connect:
            self.connect.close()


    def execute_many(self, sql, args) -> Cursor:

        try:
            cursor = self.connect.cursor()
            cursor.executemany(sql, args)
        except Exception as e:
            self.connect_db()
            cursor = self.connect.cursor()
            cursor.executemany(sql, args)
        return cursor


    def execute(self, sql: str, args: object = None) -> Cursor:
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
            _connection = pymysql.connect(host=self.config.get(self.section_name, 'host'),
                                          user=self.config.get(self.section_name, 'user'),
                                          password=self.config.get(self.section_name, 'password'),
                                          charset=self.config.get(self.section_name, 'charset'))
            cursor = _connection.cursor()
            cursor.execute('create database if not exists {}'.format(self.database_name))
            _connection.commit()
        except Exception as e:
            raise DatabaseException("Can't create database, make sure your config are correct!")
        finally:
            if _connection:
                _connection.close()
        return True


if __name__ == "__main__":
    a = db()
