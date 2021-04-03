from sklearn.feature_extraction.text import TfidfVectorizer

import os
from analog.bin.lib.utils import read_by_group
import string
from analog.bin.exception.Exceptions import *


class TfidfVector(TfidfVectorizer):
    """
    TF-IDF向量类
    """

    def __init__(self, root_path, config):
        # tf-idf 向量初始化，截取步长为2Bytes
        super().__init__(smooth_idf=True, use_idf=True, max_df=0.85, min_df=1, lowercase=False,
                         vocabulary=self.vocabulary_iter())
        self.fit_vector = None
        self.root_path = root_path
        self.config = config
        self.section_name_log = "Log"
        self.log_path = os.path.join(self.root_path, "analog/sample_set/train.txt")
        self.__fit()

    def __fit(self):
        fit_list = []
        if os.path.isfile(self.log_path):
            read_by_group(self.log_path, fit_list, pattern=self.config.get(self.section_name_log, 'log_content_pattern'))
            if len(fit_list) == 0:
                raise FileEmptyError
            self.fit_vector = self.fit_transform(fit_list)
        else:
            raise FileNotFound
            
    @staticmethod
    def vocabulary_iter():
        for i in string.printable:
            for j in string.printable:
                for k in string.printable:
                    yield i + j + k
