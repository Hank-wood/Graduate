import os
import time
import json
from datetime import datetime, timedelta
from unittest.mock import patch, PropertyMock, Mock
from pprint import pprint

from pymongo import MongoClient
import pytest
from zhihu.acttype import ActType

from manager import QuestionManager
from db import DB
from utils import *
from common import *
from monitor import TopicMonitor
from task import FetchQuestionInfo, FetchAnswerInfo


def setup_module(module):
    db = MongoClient('127.0.0.1', 27017).test
    DB.db = db  # replace db with test db


def teardown_function(function):
    for collection_name in DB.db.collection_names():
        if 'system' not in collection_name:
            DB.db[collection_name].drop()
    task_queue.clear()


@patch('huey_tasks.fetch_followers_followees', Mock())
@patch('task.FetchQuestionInfo.execute')
@patch('config.dynamic_config.topics', {"19550517": "互联网"})
def test_fetch_questions_without_previous_data(mk_execute):
    """测试数据库中没有数据的情况"""
    import main

    mk_execute.return_value = None
    tid = test_tid

    class MockQuestion:
        """
        Act as QuestionManager and zhihu.Question
        """
        def __init__(self, url, id, creation_time, title, author=''):
            self._url = self.url = url
            self.id = id
            self.creation_time = self.time = creation_time
            self.title = title
            self.author = self.asker = author
            self._session = Mock()
            self.deleted = False
            self.follower_num = 0
            self.author = Mock(id='asker')
            self.topics = ['互联网']

    t = datetime.now()
    mock_question1 = MockQuestion('http://q/1', '1', t+timedelta(1), 'question1')
    mock_question2 = MockQuestion('http://q/2', '2', t+timedelta(2), 'question2')
    mock_question3 = MockQuestion('http://q/3', '3', t+timedelta(3), 'question3')
    mock_question4 = MockQuestion('http://q/4', '4', t+timedelta(4), 'question4')

    with patch('zhihu.Topic.questions', new_callable=PropertyMock) as mock_q:
        mock_q.side_effect = [
            [mock_question1],
            [mock_question2, mock_question1],
            [mock_question2, mock_question1],
            [mock_question4, mock_question3, mock_question2, mock_question1],
            [mock_question4, mock_question3, mock_question2, mock_question1]
        ]

        def test():
            time.sleep(1)
            if mock_q.call_count == 1:
                assert len(QuestionManager.get_all_questions_one_topic(tid))==0
            if mock_q.call_count == 2:
                questions = QuestionManager.get_all_questions_one_topic(tid)
                assert questions[0]['qid'] == '2'
            if mock_q.call_count == 3:
                questions = QuestionManager.get_all_questions_one_topic(tid)
                assert questions[0]['qid'] == '2'
            if mock_q.call_count == 4:
                questions = QuestionManager.get_all_questions_one_topic(tid)
                questions.sort(key=lambda x: x['qid'])
                assert questions[0]['qid'] == '2'
                assert questions[1]['qid'] == '3'
                assert questions[2]['qid'] == '4'
                raise EndProgramException

        main.main(postroutine=test)


