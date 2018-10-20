from sklearn.feature_extraction.text import TfidfVectorizer

import string
import os
import re
from analog.bin.check.check import check_txt
from analog.bin.exception.Exceptions import *



class TfidfVector(TfidfVectorizer):
    """
    TF-IDF向量类
    """


    def __init__(self):
        # tf-idf 向量初始化，截取步长为2Bytes
        super().__init__(smooth_idf=True, use_idf=True, analyzer='char', ngram_range=(2, 2),
                         max_df=0.85, min_df=1, lowercase=False, vocabulary=self.vocabulary_iter())
        self.fit_vector = None
        self.__fit_vector()


    def __fit_vector(self):
        train_sample = []
        log_Pattern = r'^(?P<remote_addr>.*?) - (?P<remote_user>.*) \[(?P<time_local>.*?) \+[0-9]+?\] "(?P<request>.*?)" ' \
                      '(?P<status>.*?) (?P<body_bytes_sent>.*?) "(?P<http_referer>.*?)" "(?P<http_user_agent>.*?)"$'
        log_regx = re.compile(log_Pattern)
        current_path = os.path.dirname(os.path.realpath(__file__))
        sample_path = os.path.join(current_path, "../../sample_set/train.txt")
        if check_txt(sample_path) is False:
            raise FileEmptyError
        flag = False
        # 读取白样本集(日志格式)
        with open(sample_path, "r", encoding='utf-8') as file:
            line = file.readline().strip("\r\n")
            while line:
                log_tuple = log_regx.search(line)
                line = file.readline().strip("\r\n")
                if log_tuple is None and len(train_sample) == 0:
                    flag = True
                    break
                if log_tuple is not None:
                    train_sample.append(self.get_url(log_tuple.group('request')))
        if flag:
            # 读取白样本集(纯路径格式)
            with open(sample_path, "r", encoding='utf-8') as file:
                line = file.readline().strip("\r\n")
                while line:
                    train_sample.append(line)
                    line = file.readline().strip("\r\n")
        self.fit_vector = self.fit_transform(train_sample)


    @staticmethod
    def vocabulary_iter():
        for i in string.printable:
            for j in string.printable:
                yield i + j


    @staticmethod
    def get_url(request: str, unquote_url=False):
        """
        处理日志里面的request（如:GET /admin/login.php HTTP/1.0 )
        只保留路径部分
        """
        if request.startswith(("GET", "POST")):
            if unquote_url:
                res = unquote(request.strip("GET").strip())
            else:
                res = request.strip("GETPOSTHTTP/1.10").strip()
        else:
            if unquote_url:
                res = unquote(request.strip())
            else:
                res = request.strip('HTTP/1.10').strip()
        return res.ljust(2)
