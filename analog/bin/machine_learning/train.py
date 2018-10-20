import os, sys
from sklearn.svm import OneClassSVM
from analog.bin.machine_learning.TfidfVector import TfidfVector
from datetime import datetime
import re
import numpy as np
from urllib.parse import unquote
from sklearn.model_selection import ParameterGrid
import pickle


class Train:
    def __init__(self, path=None):
        self.root_path = path
        self.set_path = os.path.join(self.root_path, "analog/sample_set/")

        self.train_log_path = os.path.join(self.root_path, "analog/sample_set/train.txt")
        self.test_black_path = os.path.join(self.root_path, "analog/sample_set/test_black_log.txt")
        self.test_white_path = os.path.join(self.root_path, "analog/sample_set/test_white_log.txt")
        self.result_path = os.path.join(self.root_path, "analog/sample_set/result.txt")
        self.complete = False
        # self.test_log_path = os.path.join(self.root_path, "analog/sample_set/test.txt")


    def is_complete(self):
        return self.complete


    def set_complete(self, v: bool):
        self.complete = v


    def read_txt(self, path: str, l: list, encoding='utf-8'):
        log_Pattern = r'^(?P<remote_addr>.*?) - (?P<remote_user>.*) \[(?P<time_local>.*?) \+[0-9]+?\] "(?P<request>.*?)" ' \
                      '(?P<status>.*?) (?P<body_bytes_sent>.*?) "(?P<http_referer>.*?)" "(?P<http_user_agent>.*?)"$'
        log_regx = re.compile(log_Pattern)
        flag = False
        # 读取样本集(日志格式)
        with open(path, "r", encoding=encoding) as file:
            line = file.readline().strip("\r\n")
            while line:
                log_tuple = log_regx.search(line)
                line = file.readline().strip("\r\n")
                if log_tuple is None and len(l) == 0:
                    flag = True
                    break
                if log_tuple is not None:
                    l.append(TfidfVector.get_url(log_tuple.group('request')))
        if flag:
            # 读取样本集(纯路径格式)
            with open(path, "r", encoding=encoding) as file:
                line = file.readline().strip("\r\n")
                while line:
                    l.append(line)
                    line = file.readline().strip("\r\n")


    @staticmethod
    def get_url(request: str, unquote_url=False):
        """
        处理日志里面的request（如:GET /admin/login.php HTTP/1.0 )
        只保留路径部分
        """
        if request.startswith(("GET", "POST")):
            if unquote_url:
                res = unquote(request.strip("GETPOSTHTTP/1.10").strip())
            else:
                res = request.strip("GETPOSTHTTP/1.10").strip()
        else:
            if unquote_url:
                res = unquote(request.strip())
            else:
                res = request.strip()
        return res.ljust(2)


    def get_model(self, queue=None):
        log_Pattern = r'^(?P<remote_addr>.*?) - (?P<remote_user>.*) \[(?P<time_local>.*?) \+[0-9]+?\] "(?P<request>.*?)" ' \
                      '(?P<status>.*?) (?P<body_bytes_sent>.*?) "(?P<http_referer>.*?)" "(?P<http_user_agent>.*?)"$'
        log_regx = re.compile(log_Pattern)
        # 输出重定向
        __console__ = sys.stdout
        sys.stdout = open(os.path.join(self.root_path, "analog/log/train_log.txt"), 'w+')
        start = datetime.now()
        print("Start at {}".format(
                start.strftime("%Y/%m/%d %H:%M:%S")))

        train_example = []
        white_example = []
        black_example = []

        # 读取训练集
        self.read_txt(self.train_log_path, train_example)
        # with open(self.train_log_path, "r") as file:
        #     line = file.readline().strip("\r\n")
        #     while line:
        #         log_tuple = log_regx.search(line)
        #         line = file.readline().strip("\r\n")
        #         if log_tuple is not None:
        #             train_example.append(TfidfVector.get_url(log_tuple.group('request')))

        # 读取黑样本集
        self.read_txt(self.test_black_path, black_example)
        # with open(self.test_black_path, "r") as file:
        #     line = file.readline().strip("\r\n")
        #     while line:
        #         log_tuple = log_regx.search(line)
        #         line = file.readline().strip("\r\n")
        #         if log_tuple is not None:
        #             black_example.append(TfidfVector.get_url(log_tuple.group('request')))

        # 读取白样本集(日志格式)
        self.read_txt(self.test_white_path, white_example)
        # with open(test_white_path, "r") as file:
        #     line = file.readline().strip("\r\n")
        #     while line:
        #         log_tuple = log_regx.search(line)
        #         line = file.readline().strip("\r\n")
        #         if log_tuple is not None:
        #             white_example.append(TfidfVector.get_url(log_tuple.group('request')))

        # 读取白样本集(纯路径格式)
        # with open(self.test_white_path, "r") as file:
        #     line = file.readline().strip("\r\n")
        #     while line:
        #         white_example.append(line)
        #         line = file.readline().strip("\r\n")

        tf_idf_vector = TfidfVector()
        # 特征向量化训练样本
        train_vector = tf_idf_vector.fit_vector

        # 特征向量化黑白样本
        test_normal_vector = tf_idf_vector.transform(white_example)
        test_abnormal_vector = tf_idf_vector.transform(black_example)

        y = [1] * (len(train_example))

        # ============================================= 遍历调优参数nu与gamma ==========================================
        grid = {'gamma': np.logspace(-8, 1, 10),
                'nu': np.linspace(0.01, 0.20, 20)}

        # 核函数(rbf,linear,poly)
        kernel = 'rbf'

        # 最高准确度、召回率、F1值纪录
        max_F1 = 0
        max_Re = 0
        max_Pr = 0

        # 最高准确度、召回率、F1值时参数gamma的值
        gamma_r_F1 = 0.01
        gamma_r_Re = 0.01
        gamma_r_Pr = 0.01

        # 最高准确度、召回率、F1值时参数nu的值
        nu_r_F1 = 0
        nu_r_Re = 0
        nu_r_Pr = 0

        svdd = OneClassSVM(kernel=kernel)
        zero_count = 0
        re_gamma = 0

        total_loop = len(ParameterGrid(grid))
        process_count = 0
        for z in ParameterGrid(grid):
            process_count += 1

            queue.put_nowait("{:0.4f}".format(process_count / total_loop))
            if re_gamma == z.get('gamma'):
                if zero_count >= 4:
                    continue
            else:
                zero_count = 0
                # re_gamma = z.get('gamma')
                # zero_count = 0
            #     print("This parameter gamma({}) maybe too small. So pass it for saving time.".format(z.get('gamma')))
            #
            # if :
            #     continue
            svdd.set_params(**z)
            svdd.fit(train_vector, y)
            k = svdd.get_params()
            # 正常样本测试
            f = svdd.predict(test_normal_vector)

            TP = f.tolist().count(1)  # True positive
            FN = f.tolist().count(-1)  # False Negative

            # 异常样本测试
            f = svdd.predict(test_abnormal_vector)

            FP = f.tolist().count(1)  # False positive
            Precision = 0 if TP == 0 else (TP / (TP + FP))  # Precision
            Recall = 0 if TP == 0 else (TP / (TP + FN))  # Recall
            if Recall == 0 or Precision == 0:
                F1_score = 0
                zero_count += 1
                re_gamma = k.get('gamma')
            else:
                F1_score = 2 * Precision * Recall / (Precision + Recall)  # F1 value

            if F1_score > max_F1:
                max_F1 = F1_score
                nu_r_F1 = k.get('nu')
                gamma_r_F1 = k.get('gamma')

            if Recall > max_Re:
                max_Re = Recall
                nu_r_Re = k.get('nu')
                gamma_r_Re = k.get('gamma')

            if Precision > max_Pr:
                max_Pr = Precision
                nu_r_Pr = k.get('nu')
                gamma_r_Pr = k.get('gamma')

            print("========================== [{}] ===========================".format(
                    datetime.now().strftime("%Y/%m/%d %H:%M:%S")))
            print("nu: ", k.get('nu'), 'gamma', k.get('gamma'), )
            print("Precision: {}%".format(Precision * 100))
            print("Recall: {}%".format(Recall * 100))
            print("F1 score: {}".format(F1_score))
        print("========================== [{}] ===========================".format(
                datetime.now().strftime("%Y/%m/%d %H:%M:%S")))

        print("MAX Precision:  {:^20.6f}When Current nu: {:^20.6f} and gamma: {:0.8f}".format(max_Pr, nu_r_Pr,
                                                                                              gamma_r_Pr))
        print("MAX Recall:     {:^20.6f}When Current nu: {:^20.6f} and gamma: {:0.8f}".format(max_Re, nu_r_Re,
                                                                                              gamma_r_Re))
        print("MAX F1:         {:^20.6f}When Current nu: {:^20.6f} and gamma: {:0.8f}".format(max_F1, nu_r_F1,
                                                                                              gamma_r_F1))
        total_second = datetime.now() - start
        print("Cost {}s.".format(total_second.total_seconds()))
        queue.put_nowait("1")
        with open(os.path.join(self.root_path, "analog/cache/model.pkl"), 'wb') as file:
            svdd.set_params(kernel=kernel, nu=nu_r_F1, gamma=gamma_r_F1)
            svdd.fit(train_vector, y)
            pickle.dump(svdd, file)
        self.complete = True
