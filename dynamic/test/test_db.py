# coding: utf-8

"""
数据库相关测试
"""

from pymongo import MongoClient
from datetime import datetime
import time

from model import QuestionModel
from db import DB
from utils import *


def setup_module(module):
    db = MongoClient('127.0.0.1', 27017).test
    module.__dict__['db'] = db
    DB.db = db  # replace db with test db


def teardown_module(module):
    for collection in db.collection_names():
        db[collection].drop()


def test_find_latest():
    tid = '1234567'
    question1 = QuestionModel('url1', '1', 'asker1', datetime.now())
    question1.save(tid)
    time.sleep(1)
    question2 = QuestionModel('url2', '2', 'asker2', datetime.now())
    question2.save(tid)
    time.sleep(1)
    question3 = QuestionModel('url3', '3', 'asker3', datetime.now())
    question3.save(tid)

    for doc in db[q_col(tid)].find({}):
        print(doc)

    assert DB.find_latest_question(tid)[0]['url'] == 'url3'
    assert DB.find_latest_question(tid)[0]['qid'] == '3'
    assert DB.find_latest_question(tid)[0]['asker'] == 'asker3'
