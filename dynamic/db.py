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

    def find_user(self):
        pass

    def find_answer(self):
        pass