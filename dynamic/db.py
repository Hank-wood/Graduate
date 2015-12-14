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
        for topic in topics:
            self.__dict__[topic] = self.db[topic]
        self.user = self.db.user
        self.question = self.db.question

    def find_user(self):
        pass

    def find_latest_question(self, topic_id):
        # TODO: so ask: 如何建索引?
        question = self.question.find({'topic': topic_id}).sort({_id:1})
        return question

    def save(self):
        pass

    def bulk_save(self):
        pass