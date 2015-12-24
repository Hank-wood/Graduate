# coding: utf-8

"""
数据库相关测试
"""

from pymongo import MongoClient


def setup_module(module):
    db = MongoClient('localhost', 27017).zhihu_data
    module.__dict__['db'] = db
    db.test_db.remove({})


def teardown_module(module):
    pass


def test_simple():
    db.test_db.insert({"1": 1})
    print(list(db.test_db.find({})))