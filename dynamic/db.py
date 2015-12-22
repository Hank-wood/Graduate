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
        # return self.db[q_col(tid)].find({'topic': tid}).sort({_id:1})
        return None

    def save_question(self, question):
        self.question.insert({
            'url': question.url,
            'id': question.qid,
            'topic': question.tid,
            'time': question.time,  # TODO
        })

    def bulk_save(self):
        pass