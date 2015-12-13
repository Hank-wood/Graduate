# coding: utf-8

"""
数据库接口
"""

from pymongo import MongoClient


class DB:
    def __init__(self):
        self.db = MongoClient('localhost', 27017).zhihu_data
        self.user = self.db.user
        self.answer = self.db.answer

    def find_user(self):
        pass

    def find_answer(self):
        pass