import os
from analog.bin.exception.Exceptions import *


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
