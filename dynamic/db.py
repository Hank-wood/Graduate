# coding: utf-8

"""
数据库接口
"""

from pymongo import MongoClient
import ezcf

from config.dynamic_config import topics


class DB:
    def __init__(self):
        self.db = MongoClient('localhost', 27017).zhihu_data
        for tid in topics:
            self.__dict__[tid] = self.db[tid]
        self.user = self.db.user
        self.question = self.db.question

    def find_user(self):
        pass

    def find_latest_question(self, tid):
        # TODO: so ask: 如何建索引?
        question = self.question.find({'topic': tid}).sort({_id:1})
        return question

    def save_question(self, question):
        self.question.insert({
            'url': question.url,
            'id': question.qid,
            'topic': question.tid,
            'time': question.time,  # TODO
        })

    def bulk_save(self):
        pass