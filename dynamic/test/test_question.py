"""
抓取问题相关测试
"""

import os
import time
import json
from datetime import datetime
from unittest.mock import patch, PropertyMock, Mock

from pymongo import MongoClient
import pytest

from model import QuestionManager
from db import DB
from utils import *
from common import *


def setup_module(module):
    db = MongoClient('127.0.0.1', 27017).test
    DB.db = db  # replace db with test db


def teardown_function(function):
    for collection_name in DB.db.collection_names():
        if 'system' not in collection_name:
            DB.db[collection_name].drop()


# @pytest.mark.skipif(True, reason="testing others")
def test_find_latest():
    tid = '1234567'
    question1 = QuestionManager(tid, 'url1', '1', 'asker1', datetime.now())
    question1.save()
    time.sleep(1)
    question2 = QuestionManager(tid, 'url2', '2', 'asker2', datetime.now())
    question2.save()
    time.sleep(1)
    question3 = QuestionManager(tid, 'url3', '3', 'asker3', datetime.now())
    question3.save()

    for doc in DB.db[q_col(tid)].find({}):
        print(doc)

    assert DB.find_latest_question(tid)['url'] == 'url3'
    assert DB.find_latest_question(tid)['qid'] == '3'
    assert DB.find_latest_question(tid)['asker'] == 'asker3'


@patch('task.FetchNewAnswer.execute')
@patch('config.dynamic_config.topics', {"19550517": "互联网"})
def test_fetch_questions_without_previous_data(mk_execute):
    """测试数据库中没有数据的情况"""
    import main

    mk_execute.return_value = None
    tid = "19550517"

    class MockQuestion:
        """
        Act as QuestionManager and zhihu.Question
        """
        def __init__(self, url, id, creation_time, title, author=''):
            self.tid = tid
            self._url = self.url = url
            self.id = self.qid = id
            self.creation_time = self.time = creation_time
            self.title = title
            self.author = self.asker = author
            self._session = Mock()
            self.deleted = False

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
                assert len(QuestionManager.get_all_questions_one_topic(tid))==0
            if mock_q.call_count == 2:
                questions = QuestionManager.get_all_questions_one_topic(tid)
                assert questions[0] == mock_question2
            if mock_q.call_count == 3:
                questions = QuestionManager.get_all_questions_one_topic(tid)
                assert questions[0] == mock_question2
            if mock_q.call_count == 4:
                questions = QuestionManager.get_all_questions_one_topic(tid)
                questions.sort(key=lambda x: x.qid)
                assert questions[0] == mock_question2
                assert questions[1] == mock_question3
                assert questions[2] == mock_question4
                raise EndProgramException

        main.main(postroutine=test)


def test_fetch_questions_with_previous_data():
    """测试数据库有之前保存的 question 的情况"""
    pass


def test_get_all_questions():
    DB.db['111_q'].insert({'mm':1})
    assert dict_equal(DB.get_all_questions()[0], {'mm':1})

    DB.db['111_a'].insert({'mm':1})
    assert dict_equal(DB.get_all_questions()[0], {'mm':1})

    DB.db['111_q'].insert({'mm':2})
    assert dict_equal(DB.get_all_questions()[0], {'mm':1})
    assert dict_equal(DB.get_all_questions()[1], {'mm':2})

    DB.db['222_q'].insert({'mm':3})
    DB.db['222_q'].insert({'mm':4})
    db_results = list(DB.get_all_questions())
    db_results.sort(key=lambda x: x['mm'])
    correct = [{'mm':1}, {'mm':2}, {'mm':3}, {'mm':4}]
    for less, more in zip(correct, db_results):
        assert dict_equal(more, less)
