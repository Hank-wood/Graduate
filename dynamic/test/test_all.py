# coding: utf-8

"""
数据库相关测试
"""

import os
import time
import json
from datetime import datetime
from unittest.mock import patch, PropertyMock

from pymongo import MongoClient
import pytest

from model import QuestionModel
from db import DB
from utils import *
from common import *

db = MongoClient('127.0.0.1', 27017).test


def setup_function(function):
    DB.db = db  # replace db with test db


def teardown_function(function):
    for collection_name in db.collection_names():
        if 'system' not in collection_name:
            db[collection_name].drop()


# @pytest.mark.skipif(True, reason="testing others")
def test_config_validator():
    config = json.load(open(dynamic_config_file, encoding='utf-8'))

    assert validate_config(config)

    config['topics']['11111'] = 'non-existent'
    with pytest.raises(InvalidTopicId):
        validate_config(config)
    del config['topics']['11111']

    config['restart'] = 10
    with pytest.raises(AssertionError):
        validate_config(config)
        config['restart'] = True

    del config['topics']
    with pytest.raises(LackConfig):
        validate_config(config)


# @pytest.mark.skipif(True, reason="testing others")
def test_find_latest():
    tid = '1234567'
    question1 = QuestionModel(tid, 'url1', '1', 'asker1', datetime.now())
    question1.save()
    time.sleep(1)
    question2 = QuestionModel(tid, 'url2', '2', 'asker2', datetime.now())
    question2.save()
    time.sleep(1)
    question3 = QuestionModel(tid, 'url3', '3', 'asker3', datetime.now())
    question3.save()

    for doc in db[q_col(tid)].find({}):
        print(doc)

    assert DB.find_latest_question(tid)['url'] == 'url3'
    assert DB.find_latest_question(tid)['qid'] == '3'
    assert DB.find_latest_question(tid)['asker'] == 'asker3'


@patch('config.dynamic_config.topics', {"19550517": "互联网"})
def test_fetch_questions_without_previous_data():
    """测试数据库中没有数据的情况"""
    import main

    tid = "19550517"

    class MockQuestion:
        """
        Act as QuestionModel and zhihu.Question
        """
        def __init__(self, url, id, creation_time, title, author=''):
            self.tid = tid
            self.url = url
            self.id = self.qid = id
            self.creation_time = self.time = creation_time
            self.title = title
            self.author = self.asker = author

    t = datetime.now().replace(microsecond=0)
    mock_question1 = MockQuestion('http://q/1', '1', t, 'question1')
    mock_question2 = MockQuestion('http://q/2', '2', t, 'question2')
    mock_question3 = MockQuestion('http://q/3', '3', t, 'question3')
    mock_question4 = MockQuestion('http://q/4', '4', t, 'question4')

    with patch('zhihu.Topic.questions', new_callable=PropertyMock) as mock_q:
        mock_q.side_effect = [
            [mock_question1],
            [mock_question2, mock_question1],
            [mock_question2, mock_question1],
            [mock_question4, mock_question3, mock_question2, mock_question1],
            [mock_question4, mock_question3, mock_question2, mock_question1]
        ]

        def test():
            if mock_q.call_count == 1:
                assert len(QuestionModel.get_all(tid)) == 0
            if mock_q.call_count == 2:
                questions = QuestionModel.get_all(tid)
                assert questions[0] == mock_question2
            if mock_q.call_count == 3:
                questions = QuestionModel.get_all(tid)
                assert questions[0] == mock_question2
            if mock_q.call_count == 4:
                questions = QuestionModel.get_all(tid)
                questions.sort(key=lambda x: x.qid)
                assert questions[0] == mock_question2
                assert questions[1] == mock_question3
                assert questions[2] == mock_question4
                raise EndProgramException

        main.main(postroutine=test)


def test_fetch_questions_with_previous_data():
    """测试数据库有之前保存的 question 的情况"""
    pass


if __name__ == '__main__':
    test_monitor()
