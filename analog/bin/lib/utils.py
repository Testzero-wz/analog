import re, os
from urllib.parse import unquote
from os import walk
import gzip
from datetime import datetime
from collections import Iterable, Iterator


def read_by_group(path, l: list, group_name='request', encoding='utf-8', pattern=None, N=None, clearFlag=True):
    if pattern is None:
        pattern = r'^(?P<remote_addr>.*?) - (?P<remote_user>.*) \[(?P<time_local>.*?) \+[0-9]+?\] "(?P<request>.*?)" ' \
                  '(?P<status>.*?) (?P<body_bytes_sent>.*?) "(?P<http_referer>.*?)" "(?P<http_user_agent>.*?)"$'
    if clearFlag:
        l.clear()
    log_regx = re.compile(pattern)
    c = 0
    # 读取样本集(日志格式)
    if isinstance(path, str):
        file = open(path, "r", encoding=encoding)
    else:
        file = path
    try:
        line = file.readline().strip(" \r\n")
        while line:
            log_tuple = log_regx.search(line)
            if len(line) != 0 and line[0] != "#":
                if log_tuple is not None:
                    if isinstance(group_name, str):
                        l.append(log_tuple.group(group_name))
                    elif isinstance(group_name, list):
                        l.append([log_tuple.group(g) for g in group_name])
                    c += 1
                    if N is not None and c == N:
                        break
            line = file.readline().strip(" \r\n")
    except Exception as e:
        raise e
    finally:
        if file:
            file.close()
    return c


def log_int(num):
    try:
        return int(num)
    except ValueError:
        return "-"
    except Exception as e:
        raise e


def get_url(request: str, unquote_url=False):
    """
    处理日志里面的request（如:GET /admin/login.php HTTP/1.0 )
    只保留路径部分
    """
    if request.startswith(("GET", "POST")):
        if unquote_url:
            res = unquote(request.strip("GETPOSTHTTP/1.102").strip())
        else:
            res = request.strip("GETPOSTHTTP/1.102").strip()
    else:
        if unquote_url:
            res = unquote(request.strip())
        else:
            res = request.strip()
    return res.ljust(2)


def fetch(res: list, index: int, proc=None):
    for item in res:
        if proc:
            yield proc(item[index])
        else:
            yield item[index]


def fp_gen(log_path, pattern=None, encoding='utf-8'):
    """
    return access log file fp
    """
    if pattern is None:
        pattern = ".*access.*"
    for (base_dir, dirnames, filenames) in walk(log_path):
        for file in filenames:
            if re.search(pattern, file) is None:
                continue
            full_path = os.path.join(base_dir, file)
            if is_gzip(file):
                yield gzip.open(full_path, "rt", encoding=encoding)
            else:
                yield open(full_path, "r", encoding=encoding)


class LogRead:

    def __init__(self, file_path, encoding="utf-8"):
        self.file_path = file_path
        self.encoding = encoding
        self.is_gz = self.is_gzip(file_path)
        self.file_handle = None

    def __enter__(self):
        if self.is_gz:
            self.file_handle = gzip.open(self.file_path, "rt", encoding=self.encoding)
        else:
            self.file_handle = open(self.file_path, "r", encoding=self.encoding)
        return self.file_handle

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file_handle is not None:
            self.file_handle.close()

    @staticmethod
    def is_gzip(file_name: str):
        return file_name.endswith(".gz")


def reverse_read_lines(file_path, n=None, linefeed="\n", encoding="utf-8", buf_size=8192):
    """
    反向读取lines，支持大文件
    :param file_path: 文件路径
    :param n: 读取的行数，默认全部读取
    :param linefeed: 换行符
    :param encoding: 读取文件的编码
    :param buf_size: 单次读取的字节buffer大小
    :return:
    """
    with LogRead(file_path, encoding=encoding) as fp:
        tmp_buff = None
        fp.seek(0, os.SEEK_END)
        pointer = remaining_size = fp.tell()
        count = 0
        while remaining_size > 0:
            pointer = max(0, pointer - buf_size)
            fp.seek(pointer)
            buffer = fp.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            lines = buffer.split(linefeed)
            if tmp_buff is not None:
                if lines[-1] == '' and (n is None or count < n):
                    count += 1
                    yield tmp_buff
                else:
                    lines[-1] += tmp_buff

            tmp_buff = lines[0]
            for i in range(len(lines) - 1, 0, -1):
                if lines[i] and (n is None or count < n):
                    count += 1
                    yield lines[i]
        # 单行的情况，返回已读部分
        if tmp_buff is not None and count != n:
            yield tmp_buff


def stop_iter(_iter):
    if not isinstance(_iter, Iterable):
        raise TypeError
    if not isinstance(_iter, Iterator):
        _iter = iter(_iter)
    p = next(_iter)
    try:
        while True:
            q = next(_iter)
            yield p, False
            p = q
    except StopIteration:
        yield p, True


def is_gzip(file_name):
    return file_name.endswith(".gz")


def log2db_time(time_str, log_str="%d/%b/%Y:%H:%M:%S", db_str="%Y/%m/%d %H:%M:%S"):
    """ 转换时间格式 '%d/%b/%Y:%H:%M:%S' => '%Y/%m/%d %H:%M:%S'  """
    t = datetime.strptime(time_str, log_str)
    return t.strftime(db_str)


def db_time2datetime(time_str, db_str="%Y/%m/%d %H:%M:%S"):
    return datetime.strptime(time_str, db_str)
