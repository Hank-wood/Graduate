"""
抓取问题相关测试
"""

import os
import time
import json
import logging
from datetime import datetime
from unittest.mock import patch, PropertyMock, Mock
from pprint import pprint
from functools import partial

from pymongo import MongoClient
import pytest
from zhihu.acttype import ActType

from manager import QuestionManager
from db import DB
from utils import *
from common import *
from monitor import TopicMonitor
from task import FetchQuestionInfo, FetchAnswerInfo
from huey_tasks import _fetch_question_follower

_fetch_question_follower = partial(_fetch_question_follower, db_name='test')


def setup_module(module):
    db = MongoClient('127.0.0.1', 27017).test
    DB.db = db  # replace db with test db
    logging.basicConfig(level=logging.INFO)


def teardown_function(function):
    for collection_name in DB.db.collection_names():
        if 'system' not in collection_name:
            DB.db[collection_name].drop()
    question_task_queue.clear()
    answer_task_queue.clear()


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

    latest = DB.find_latest_question(tid)
    assert latest['url'] == 'url3'
    assert latest['qid'] == '3'
    assert latest['asker'] == 'asker3'


@pytest.mark.skipif(skip, reason="")
@patch('huey_tasks.fetch_followers_followees', Mock())
def test_initiate_monitor_with_previous_questions():
    """测试数据库有之前保存的 question 的情况"""
    import monitor
    prefix = 'https://www.zhihu.com/question/'
    DB.db[q_col(test_tid)].insert({
        'topic': test_tid,
        'url': prefix + '1111/',
        'asker': '',
        'active': True
    })
    DB.db[q_col(test_tid)].insert({
        'topic': test_tid,
        'url': prefix + '2222?sort=created',
        'asker': '',
        'active': True
    })
    DB.db[q_col(test_tid2)].insert({
        'topic': test_tid,
        'url': prefix + '3333/',
        'asker': '',
        'active': True
    })
    DB.db[q_col(test_tid2)].insert({
        'topic': test_tid,
        'url': prefix + '4444?sort=created',
        'asker': '',
        'active': True
    })
    _ = monitor.TopicMonitor()
    urls = [task.question._url for task in question_task_queue]
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
    time1 = datetime.now().replace(microsecond=0)
    time2 = time1 + timedelta(hours=1)
    time3 = time2 + timedelta(hours=1)
    time4 = time3 + timedelta(hours=1)

    # 因为要获取 deleted 属性,故使用真实的问题url
    DB.db[q_col(test_tid)].insert({
        'asker': 'asker1',
        'topic': test_tid,
        'qid': '38717319',
        'url': prefix + '38717319/',
        'follower': [],
        'active': True
    })
    DB.db[q_col(test_tid)].insert({
        'asker': 'asker2',
        'topic': test_tid,
        'qid': '39880296',
        'url': prefix + '39880296/',
        'follower': [],
        'active': True
    })
    DB.db[a_col(test_tid)].insert({
        'qid': '38717319',
        'aid': '1',
        'url': prefix + '38717319/answer/1',
        'upvoters': [],
        'commenters': [],
        'collectors': [],
        'time': time1
    })
    DB.db[a_col(test_tid)].insert({
        'qid': '38717319',
        'aid': '2',
        'url': prefix + '38717319/answer/2',
        'upvoters': [
            {'uid':'1', 'time': time3},
            {'uid':'2', 'time': time4},
        ],
        'commenters': [],
        'collectors': [],
        'time': time2
    })
    _ = TopicMonitor()

    # 初始化 FetchQuestionInfo 时 FetchAnswerInfo 进入 task_queue
    # 然后 FetchQuestionInfo 进入 task_queue
    assert isinstance(answer_task_queue[0], FetchAnswerInfo)
    assert answer_task_queue[0].last_update_time == time1
    assert isinstance(answer_task_queue[1], FetchAnswerInfo)
    assert answer_task_queue[1].last_update_time == time4
    old_answers = set([task.answer.id for task in list(answer_task_queue)])
    assert old_answers == {1, 2}

    assert isinstance(question_task_queue[0], FetchQuestionInfo)
    assert question_task_queue[0].qid == '38717319'
    assert question_task_queue[0].last_update_time == time2

    # 测试删除没有答案的问题
    assert DB.db[a_col(test_tid)].find_one({'qid': '39880296'}) is None


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
@patch('huey_tasks.fetch_question_follower', _fetch_question_follower)
@patch('huey_tasks.get_client')
def test_update_question_info(mock_client):
    """
    测试问题 follower 更新，答案更新, 测试question follower 不会包含提问回答者
    """
    mock_question = Mock(refresh=Mock(), id='q1', url='q/1/', deleted=False,
                         follower_num=0, answer_num=0, answers=deque(),
                         followers=deque(), author=Mock(id='asker'))
    mock_client.return_value = Mock(question=Mock(return_value=mock_question))
    tid = test_tid
    QuestionManager.save_question(tid, mock_question.url, mock_question.id,
                                  datetime.now(), 'asker', 'title')
    task = FetchQuestionInfo(tid, mock_question)

    mock_question.follower_num = 1
    mock_question.followers.appendleft(Mock(id='asker'))
    task.execute()
    assert question_task_queue.popleft() is task

    mock_question.answer_num = 1
    mock_question.answers.appendleft(
        Mock(question=mock_question, url='answer/1', author=Mock(id='uid1'),
             creation_time=datetime.now(), id='aid1'))
    mock_question.follower_num = 2
    mock_question.followers.appendleft(Mock(id='uid1'))
    task.execute()
    assert answer_task_queue.popleft().answer.id == 'aid1'
    assert question_task_queue.popleft() is task

    mock_question.answer_num = 2
    mock_question.answers.appendleft(
        Mock(question=mock_question, url='answer/2', author=Mock(id='uid2'),
             creation_time=datetime.now(), id='aid2'))
    mock_question.follower_num = 5  # asker + 2 ans + 2 pure follower
    mock_question.followers = deque([
        Mock(id='fid2', activities=[
            Mock(type=ActType.FOLLOW_QUESTION, content=Mock(id='q1'),
                 time=datetime.now())
        ]),
        Mock(id='uid2'),  # 模仿一个answerer
        Mock(id='fid1', activities=[
            Mock(type=ActType.FOLLOW_QUESTION, content=Mock(id='q1'),
                 time=datetime.now())
        ])
    ]) + mock_question.followers
    task.execute()
    assert task.follower_num == 5
    assert QuestionManager.get_question_follower(tid, 'q1') == {'fid1', 'fid2'}
    assert answer_task_queue.popleft().answer.id == 'aid2'
    assert question_task_queue.popleft() is task

    mock_question.follower_num = 8
    mock_question.followers = deque([
        Mock(id='fid5', activities=[
            Mock(type=ActType.FOLLOW_QUESTION, content=Mock(id='q1'),
                 time=datetime.now())
        ]),
        Mock(id='fid4', activities=[
            Mock(type=ActType.FOLLOW_QUESTION, content=Mock(id='q1'),
                 time=datetime.now())
        ]),
        Mock(id='fid3', activities=[
            Mock(type=ActType.FOLLOW_QUESTION, content=Mock(id='q1'),
                 time=datetime.now())
        ]),
    ]) + mock_question.followers
    task.execute()
    assert task.follower_num == 5
    assert QuestionManager.get_question_follower(tid, 'q1') == {
        'fid1', 'fid2'
    }
    assert question_task_queue.popleft() is task

    mock_question.answers.appendleft(
        Mock(question=mock_question, url='answer/3', author=Mock(id='uid3'),
             creation_time=datetime.now(), id='aid3'))
    mock_question.answer_num = 3
    task.execute()
    assert task.follower_num == 8
    assert [f['uid'] for f in DB.get_question_follower(tid, 'q1')] == \
                                    ['fid1', 'fid2', 'fid3', 'fid4', 'fid5']
    # 测试 limit 属性
    assert QuestionManager.get_question_follower(tid, 'q1', limit=1) == {'fid5'}
    assert QuestionManager.get_question_follower(tid, 'q1', limit=2) == {
        'fid4', 'fid5'
    }


@pytest.mark.skipif(skip, reason="")
@patch('huey_tasks.fetch_followers_followees', Mock())
def test_get_question_attrs():
    QuestionManager.save_question(test_tid, 'http:/q/1', '1', datetime.now(),
                                  'asker', 'title')
    assert QuestionManager.get_question_attrs(test_tid, '1', 'url') == 'http:/q/1'
    assert QuestionManager.get_question_attrs(test_tid, '1', 'qid', 'title') == \
           ['1', 'title']


@patch('huey_tasks.fetch_followers_followees', Mock())
def test_get_question_follower_num():
    QuestionManager.save_question(test_tid, 'http:/q/1', '1', datetime.now(),
                                  'asker', 'title')
    QuestionManager.save_question(test_tid, 'http:/q/2', '2', datetime.now(),
                                  'asker', 'title')
    assert QuestionManager.get_question_follower_num(test_tid, '1') == 0
    QuestionManager.add_question_follower(test_tid, '1', ['f1', 'f2'])
    assert QuestionManager.get_question_follower_num(test_tid, '1') == 2


def test_set_inactive():
    QuestionManager.save_question(test_tid, 'http:/q/1', '1', datetime.now(),
                                  'asker', 'title')
    QuestionManager.set_question_inactive(test_tid, '1')
    assert QuestionManager.get_question_attrs(test_tid, '1', 'active') == False


def test_skip_inactive():
    QuestionManager.save_question(test_tid, 'http:/q/1', '1', datetime.now(),
                                  'asker', 'title')
    QuestionManager.set_question_inactive(test_tid, '1')
    _ = TopicMonitor()
    assert len(question_task_queue) == 0