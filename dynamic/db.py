# coding: utf-8

"""
数据库接口
"""

from pymongo import MongoClient
import ezcf

from config.dynamic_config import topics
from utils import *


class DB:
    def __init__(self):
        self.db = MongoClient('localhost', 27017).zhihu_data

    def find_user(self):
        pass

    def find_latest_question(self, tid):
        # TODO: so ask: 如何建索引?
        return self.db[q_col(tid)].sort({time:1}).limit(1)

    def save_question(self, question, tid):
        self.db[q_col(tid)].insert({
            'url': question.url,
            'qid': question.qid,
            'time': question.time,
            'asker': 'test_user',
            'answers': question.answers
        })

    def bulk_save(self):
        pass