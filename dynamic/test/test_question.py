"""
抓取问题相关测试
"""

import os
import time
import json
from datetime import datetime
from unittest.mock import patch, PropertyMock, Mock
from pprint import pprint

from pymongo import MongoClient
import pytest
from zhihu.acttype import ActType

from manager import QuestionManager
from db import DB
from utils import *
from common import *
from task import FetchQuestionInfo, FetchAnswerInfo


def setup_module(module):
    db = MongoClient('127.0.0.1', 27017).test
    DB.db = db  # replace db with test db


def teardown_function(function):
    for collection_name in DB.db.collection_names():
        if 'system' not in collection_name:
            DB.db[collection_name].drop()
    task_queue.clear()


def teardown_module(module):
    DB.db.client.close()

skip = False


@pytest.mark.skipif(skip, reason="")
@patch('huey_tasks.fetch_followers_followees', Mock())
def test_find_latest():
    tid = '1234567'
    QuestionManager.save_question(tid, 'url1', '1', datetime.now(), 'asker1', '')
    time.sleep(1)
    QuestionManager.save_question(tid, 'url2', '2', datetime.now(), 'asker2', '')
    time.sleep(1)
    QuestionManager.save_question(tid, 'url3', '3', datetime.now(), 'asker3', '')

    for doc in DB.db[q_col(tid)].find({}):
        print(doc)

    latest = DB.find_latest_question(tid)
    assert latest['url'] == 'url3'
    assert latest['qid'] == '3'
    assert latest['asker'] == 'asker3'


@pytest.mark.skipif(skip, reason="")
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
            self.id = self.qid = id
            self.creation_time = self.time = creation_time
            self.title = title
            self.author = self.asker = author
            self._session = Mock()
            self.deleted = False
            self.follower_num = 0
            self.author = Mock(id='asker')

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


@pytest.mark.skipif(skip, reason="")
@patch('huey_tasks.fetch_followers_followees', Mock())
def test_initiate_monitor_with_previous_questions():
    """测试数据库有之前保存的 question 的情况"""
    import monitor
    prefix = 'https://www.zhihu.com/question/'
    DB.db[q_col(test_tid)].insert({
        'topic': test_tid,
        'url': prefix + '1111/'
    })
    DB.db[q_col(test_tid)].insert({
        'topic': test_tid,
        'url': prefix + '2222?sort=created'
    })
    DB.db[q_col(test_tid2)].insert({
        'topic': test_tid,
        'url': prefix + '3333/'
    })
    DB.db[q_col(test_tid2)].insert({
        'topic': test_tid,
        'url': prefix + '4444?sort=created'
    })
    _ = monitor.TopicMonitor(Mock())
    urls = [task.question._url for task in task_queue]
    assert set(urls) == {
        prefix + '1111?sort=created',
        prefix + '2222?sort=created',
        prefix + '3333?sort=created',
        prefix + '4444?sort=created'
    }


def test_initiate_fetchquestioninfo_with_previous_answers():
    """
    先在数据库中写入问题和答案
    :return:
    """
    prefix = 'https://www.zhihu.com/question/'
    DB.db[q_col(test_tid)].insert({
        'topic': test_tid,
        'qid': '1111',
        'url': prefix + '1111/',
        'follower': []
    })
    DB.db[q_col(test_tid)].insert({
        'topic': test_tid,
        'qid': '2222',
        'url': prefix + '2222/',
        'follower': []
    })
    DB.db[a_col(test_tid)].insert({
        'qid': '1111',
        'aid': '1',
        'url': prefix + '1111/answer/1',
        'upvoters': [],
        'commenters': [],
        'collectors': []
    })
    DB.db[a_col(test_tid)].insert({
        'qid': '1111',
        'aid': '2',
        'url': prefix + '1111/answer/2',
        'upvoters': [],
        'commenters': [],
        'collectors': []
    })
    question1 = Mock(deleted=False, id='1111', author=Mock(id='1'))
    question2 = Mock(deleted=False, id='2222', author=Mock(id='2'))
    _ = FetchQuestionInfo(test_tid, question1, from_db=True)
    _ = FetchQuestionInfo(test_tid, question2, from_db=True)
    old_answers = set([task.answer.id for task in task_queue])
    assert old_answers == {1, 2}


@pytest.mark.skipif(skip, reason="")
@patch('huey_tasks.fetch_followers_followees', Mock())
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


@pytest.mark.skipif(skip, reason="")
@patch('huey_tasks.fetch_followers_followees', Mock())
def test_update_question_info():
    """
    测试问题 follower 更新，答案更新, 测试question follower 不会包含提问回答者
    """
    mock_question = Mock(refresh=Mock(), id='q1', url='q/1/', deleted=False,
                         follower_num=0, answer_num=0, answers=deque(),
                         followers=deque(), author=Mock(id='asker'))
    tid = test_tid
    QuestionManager.save_question(tid, mock_question.url, mock_question.id,
                                  datetime.now(), 'asker', 'title')
    task = FetchQuestionInfo(tid, mock_question)

    mock_question.follower_num = 1
    mock_question.followers.appendleft(Mock(id='asker'))
    task.execute()
    assert task_queue.popleft() is task

    mock_question.answer_num = 1
    mock_question.answers.appendleft(
        Mock(question=mock_question, url='answer/1', author=Mock(id='uid1'),
             creation_time=datetime.now(), id='aid1'))
    mock_question.follower_num = 2
    mock_question.followers.appendleft(Mock(id='uid1'))
    task.execute()
    assert task_queue.popleft().answer.id == 'aid1'
    assert task_queue.popleft() is task

    mock_question.answer_num = 2
    mock_question.answers.appendleft(
        Mock(question=mock_question, url='answer/2', author=Mock(id='uid2'),
             creation_time=datetime.now(), id='aid2'))
    mock_question.follower_num = 5  # asker + 2 ans + 2 pure follower
    mock_question.followers.extendleft([
        Mock(id='fid2', activities=[
            Mock(type=ActType.FOLLOW_QUESTION, content=Mock(id='q1'),
                 time=datetime.now())
        ]),
        Mock(id='uid2'),
        Mock(id='fid1', activities=[
            Mock(type=ActType.FOLLOW_QUESTION, content=Mock(id='q1'),
                 time=datetime.now())
        ])
    ])
    task.execute()
    assert task.follower_num == 5
    assert QuestionManager.get_question_follower(tid, 'q1') == {'fid1', 'fid2'}
    assert task_queue.popleft().answer.id == 'aid2'
    assert task_queue.popleft() is task

    mock_question.follower_num = 6
    mock_question.followers.appendleft(
        Mock(id='fid3', activities=[
            Mock(type=ActType.FOLLOW_QUESTION, content=Mock(id='q1'),
                 time=datetime.now())
        ]))
    task.execute()
    assert task.follower_num == 6
    assert QuestionManager.get_question_follower(tid, 'q1') == {
        'fid1', 'fid2', 'fid3'
    }
    assert task_queue.popleft() is task
    pprint(DB.get_question_follower(tid, 'q1'))

    # 测试 limit 属性
    assert QuestionManager.get_question_follower(tid, 'q1', limit=1) == {'fid3'}
    assert QuestionManager.get_question_follower(tid, 'q1', limit=2) == {
        'fid3', 'fid2'
    }


@pytest.mark.skipif(skip, reason="")
def test_get_question_attrs():
    QuestionManager.save_question(test_tid, 'http:/q/1', '1', datetime.now(),
                                  'asker', 'title')
    assert QuestionManager.get_question_attrs(test_tid, '1', 'url') == 'http:/q/1'
    assert QuestionManager.get_question_attrs(test_tid, '1', 'qid', 'title') == \
           ['1', 'title']


def test_get_question_follower_num():
    QuestionManager.save_question(test_tid, 'http:/q/1', '1', datetime.now(),
                                  'asker', 'title')
    QuestionManager.save_question(test_tid, 'http:/q/2', '2', datetime.now(),
                                  'asker', 'title')
    assert QuestionManager.get_question_follower_num(test_tid, '1') == 0
    QuestionManager.add_question_follower(test_tid, '1', ['f1', 'f2'])
    assert QuestionManager.get_question_follower_num(test_tid, '1') == 2
