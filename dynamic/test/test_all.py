# coding: utf-8

"""
数据库相关测试
"""

import os
import time
from datetime import datetime
from unittest.mock import patch, PropertyMock

from pymongo import MongoClient
import pytest

from model import QuestionModel
from db import DB
from utils import *
from common import *

db = MongoClient('127.0.0.1', 27017).test


def setup_module(module):
    DB.db = db  # replace db with test db


def teardown_module(module):
    for collection in db.collection_names():
        db[collection].drop()


@pytest.mark.skipif(True, reason="testing others")
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


@patch('config.dynamic_config.topics', {"19550517": "互联网"})
def test_fetch_questions_without_previous_data():
    """测试数据库中没有数据的情况"""
    import main
    class MockQuestion:
        def __init__(self, url, id, creation_time, title, author=None):
            self.url = url
            self.id = id
            self.creation_time = creation_time
            self.title = title
            self.author = author

    with patch('zhihu.Topic.questions', new_callable=PropertyMock) as mock_q:
        mock_q.side_effect = [[
                MockQuestion('http://q/1', '1', datetime.now(), 'question1')],
            [
                MockQuestion('http://q/1', '1', datetime.now(), 'question1')],
            [
                MockQuestion('http://q/2', '2', datetime.now(), 'question2'),
                MockQuestion('http://q/1', '1', datetime.now(), 'question1')],
            [
                MockQuestion('http://q/4', '4', datetime.now(), 'question4'),
                MockQuestion('http://q/3', '3', datetime.now(), 'question3'),
                MockQuestion('http://q/2', '2', datetime.now(), 'question2'),
                MockQuestion('http://q/1', '1', datetime.now(), 'question1')
            ]
        ]

        def stop(count):
            if count == 3:
                raise EndProgramException

        main.main(routine=stop)


def test_fetch_questions_with_previous_data():
    """测试数据库有之前保存的 question 的情况"""
    pass


if __name__ == '__main__':
    test_monitor()
