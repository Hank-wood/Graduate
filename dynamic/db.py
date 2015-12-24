# coding: utf-8

"""
数据库接口
"""

from pymongo import MongoClient
import ezcf

from config.dynamic_config import topics
from utils import *


class DB:
    db = MongoClient('127.0.0.1', 27017).zhihu_data

    @classmethod
    def find_user(cls):
        pass

    @classmethod
    def find_latest_question(cls, tid):
        # TODO: so ask: 如何建索引?
        return cls.db[q_col(tid)].find().sort('time', -1).limit(1)

    @classmethod
    def save_question(cls, question, tid):
        cls.db[q_col(tid)].insert({
            'url': question.url,
            'qid': question.qid,
            'time': question.time,
            'asker': question.asker,
            'answers': question.answers
        })

    @classmethod
    def bulk_save(cls):
        pass