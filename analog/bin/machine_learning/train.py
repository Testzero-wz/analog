import os, sys
from sklearn.svm import OneClassSVM
from analog.bin.machine_learning.TfidfVector import TfidfVector
from datetime import datetime
import numpy as np
from sklearn.model_selection import ParameterGrid
import pickle
from analog.bin.lib.utils import read_by_group
from analog.bin.logger.logger import Logger


class Train:
    def __init__(self, path=None, config=None, test_flag=False):
        self.root_path = path
        self.set_path = os.path.join(self.root_path, "analog/sample_set/")
        self.train_log_path = os.path.join(self.root_path, "analog/sample_set/train.txt")
        self.test_black_path = os.path.join(self.root_path, "analog/sample_set/test_black_log.txt")
        self.test_white_path = os.path.join(self.root_path, "analog/sample_set/test_white_log.txt")
        self.result_path = os.path.join(self.root_path, "analog/sample_set/result.txt")
        self.complete = False
        self.config = config
        self.test = test_flag
        self.section_name_log = "Log"
        self.log_path = os.path.join(self.root_path, "analog/logs/train_log.log")

    def is_complete(self):
        return self.complete

    def set_complete(self, v: bool):
        self.complete = v

    def get_model(self, queue=None):

        start = datetime.now()
        # Since logger is not pickleable until python 3.7,
        # we can init logger within this function.
        train_logger = Logger(logger_name="train_logger",
                              log_path=self.log_path)

        train_logger.register_log_function("calc", "CALCU")
        train_logger.register_log_function("split", "SPLIT")
        train_logger.register_log_function("start", "START")
        train_logger.register_log_function("end", "-END-")
        train_logger.register_log_function("result", "RESULT")
        train_logger.start("Start Training.")
        train_example = []
        white_example = []
        black_example = []

        pattern = self.config.get(self.section_name_log, 'log_content_pattern')
        # 读取训练集
        read_by_group(self.train_log_path, train_example, pattern=pattern)

        # 读取黑样本集
        read_by_group(self.test_black_path, black_example, pattern=pattern)

        # 读取白样本集
        read_by_group(self.test_white_path, white_example, pattern=pattern)

        # 特征向量化训练样本
        tf_idf_vector = TfidfVector(self.root_path, self.config)
        train_vector = tf_idf_vector.fit_vector

        # 特征向量化黑/白样本
        test_normal_vector = tf_idf_vector.transform(white_example)
        test_abnormal_vector = tf_idf_vector.transform(black_example)
        # test_param_x = tf_idf_vector.transform(white_example + black_example)
        # test_param_y = [1] * len(white_example) + [-1] * len(black_example)
        # ============================================= 遍历调优参数nu与gamma ==========================================
        grid = {'gamma': np.logspace(-9, 1, 10),
                'nu': np.linspace(0.00001, 0.2, 100)}
        # ======================================= GridSearchCV遍历调优参数nu与gamma ======================================
        # scores = "f1"
        # clf = GridSearchCV(OneClassSVM(), grid, scoring=scores)
        # clf.fit(test_param_x, test_param_y)
        # ==============================================================================================================

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
                if zero_count >= 6:
                    continue
            else:
                zero_count = 0
            svdd = OneClassSVM(**z)
            svdd.fit(train_vector)
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

            train_logger.split("=" * 60)
            train_logger.calc("nu: %.08f , gamma: %.04f" % (k.get('nu'), k.get('gamma')))
            train_logger.calc("precision: {}%".format(Precision * 100))
            train_logger.calc("recall: {}%".format(Recall * 100))
            train_logger.calc("f1 score: {}".format(F1_score))

        train_logger.split("=" * 60)
        train_logger.result(
            "MAX Precision:{:^20.6f}When Current nu: {:^20.6f} and gamma: {:0.8f}".format(max_Pr, nu_r_Pr,
                                                                                          gamma_r_Pr))
        train_logger.result(
            "MAX Recall:   {:^20.6f}When Current nu: {:^20.6f} and gamma: {:0.8f}".format(max_Re, nu_r_Re,
                                                                                          gamma_r_Re))
        train_logger.result(
            "MAX F1:       {:^20.6f}When Current nu: {:^20.6f} and gamma: {:0.8f}".format(max_F1, nu_r_F1,
                                                                                          gamma_r_F1))
        total_second = datetime.now() - start
        train_logger.end("Cost {}s.".format(total_second.total_seconds()))
        queue.put_nowait("1")
        with open(os.path.join(self.root_path, "analog/cache/model.pkl"), 'wb') as file:
            # svdd = OneClassSVM(**clf.best_params_)
            svdd.set_params(kernel=kernel, nu=nu_r_F1, gamma=gamma_r_F1)
            svdd.fit(train_vector)
            pickle.dump(svdd, file)
        self.complete = True
        # sys.stdout = __console__
