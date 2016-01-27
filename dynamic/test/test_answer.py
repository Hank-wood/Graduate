import os
import time
import json
from datetime import datetime, timedelta, time, date
from collections import deque
from unittest.mock import patch, Mock
from pprint import pprint

import zhihu
import pytest
from pymongo import MongoClient
from freezegun import freeze_time

import utils
from model import AnswerManager
from db import DB
from task import FetchAnswerInfo
from utils import *
from common import *


def setup_module(module):
    db = MongoClient('127.0.0.1', 27017).test
    DB.db = db  # replace db with test db
    module.__dict__['tid'] = '123456'
    module.__dict__['aid'] = '111111'
    module.__dict__['qid'] = '000000'
    module.__dict__['author_id'] = 'author_id'


def teardown_function(function):
    for collection_name in DB.db.collection_names():
        if 'system' not in collection_name:
            DB.db[collection_name].drop()
    task_queue.clear()


@freeze_time("2016-01-09 13:01")  # now().time > creation_time, 防止跨天
@patch('task.FetchAnswerInfo.get_upvote_time')
@patch('task.FetchAnswerInfo.get_collect_time')
def test_fetch_answers_without_previous_data(mock_upvote_time,
                                             mock_collect_time):
    # mongodb can't store microsecond
    t1 = datetime.now().replace(microsecond=0)
    mock_upvote_time.side_effect = mock_collect_time.side_effect \
                                 = [t1+timedelta(i) for i in range(10)]

    mock_answer = Mock(url=None, id=aid, creation_time=None, collect_num=0,
                       upvoters=deque(), comments=[], collections=[],
                       question=Mock(title='test question'), deleted=False)
    refresh = Mock()
    mock_question = Mock(id=qid)
    mock_author = Mock(id=author_id)

    # 只有 upvoters 需要 appendleft 来模拟新 upvoter 在上面
    def update_attrs():
        if refresh.call_count == 1:
            mock_answer.upvoters.appendleft(Mock(id='up1'))
        elif refresh.call_count == 2:
            mock_answer.upvoters.appendleft(Mock(id='up2'))
            mock_answer.comments.append(Mock(cid=1, author=Mock(id='cm1'),
                                             creation_time=datetime(2016,1,9,13,1,0)))
        elif refresh.call_count == 3:
            mock_answer.upvoters.appendleft(Mock(id='up3'))
            mock_answer.comments.append(Mock(cid=2, author=Mock(id='cm2'),
                                             creation_time=datetime(2016,1,9,13,2,0)))
            mock_answer.collections.append(Mock(id=1, owner=Mock(id='cl1')))
            mock_answer.collect_num += 1
        elif refresh.call_count == 4:
            mock_answer.comments.append(Mock(cid=3, author=Mock(id='cm1'),
                                             creation_time=datetime(2016,1,9,13,3,0)))
        elif refresh.call_count == 5:
            mock_answer.comments.append(Mock(cid=4, author=Mock(id='cm3'),
                                             creation_time=datetime(2016,1,9,13,4,0)))
            mock_answer.comments.append(Mock(cid=5, author=Mock(id='cm1'),
                                             creation_time=datetime(2016,1,9,13,5,0)))
        elif refresh.call_count == 6:
            # test deleted answer
            mock_answer.deleted = True

    refresh.side_effect = update_attrs
    mock_answer.configure_mock(refresh=refresh, question=mock_question,
                               author=mock_author)

    task = FetchAnswerInfo(tid=tid, answer=mock_answer)
    answer_info = {
        'topic': tid, 'aid': aid, 'qid': qid, 'answerer': author_id,
        'upvoters': [], 'commenters': [], 'collectors': []
    }
    day = datetime.now().date()
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)

    # call_count = 1
    task.execute()
    answer_info['upvoters'].append({'uid':'up1', 'time':t1})
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)

    # call_count = 2
    task.execute()
    answer_info['upvoters'].append({'uid':'up2', 'time':t1+timedelta(1)})
    answer_info['commenters'].append({'uid':'cm1', 'cid':1,
                                      'time':datetime.combine(day, time(13,1))})
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)
    assert task.manager.lastest_comment_time == datetime.combine(day, time(13,1))

    # call_count = 3
    task.execute()
    answer_info['upvoters'].append({'uid':'up3', 'time':t1+timedelta(2)})
    answer_info['commenters'].append({'uid':'cm2', 'cid':2,
                                      'time':datetime.combine(day, time(13,2))})
    answer_info['collectors'].append({'uid':'cl1', 'time':t1, 'cid':1})
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)
    assert task.manager.lastest_comment_time == datetime.combine(day, time(13,2))

    # test adding comment posted by same person
    task.execute()
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)
    assert task.manager.lastest_comment_time == datetime.combine(day, time(13,2))

    task.execute()
    answer_info['commenters'].append({'uid':'cm3', 'cid':4,
                                     'time':datetime.combine(day, time(13,4))})
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)
    assert task.manager.lastest_comment_time == datetime.combine(day, time(13,4))

    task.execute()
    assert DB.find_one_answer(tid, aid) == None


@patch('task.FetchAnswerInfo.get_upvote_time')
@patch('task.FetchAnswerInfo.get_collect_time')
def test_fetch_answers_with_previous_data(mock_collect_time, mock_upvote_time):
    answer_info = {
        'topic': str(tid),
        'aid': str(aid),
        'url': 'https://zhihu.com/answer/1',
        'qid': str(qid),
        'time': datetime(2016, 1, 8, 19, 30, 1),
        'answerer': author_id,
        'upvoters': [
            {'uid':'up1', 'time':datetime(2016, 1, 8, 19, 30, 1)},
            {'uid':'up2', 'time':datetime(2016, 1, 8, 19, 40, 1)},
            {'uid':'up3', 'time':datetime(2016, 1, 9, 3, 50, 2)}
        ],
        'commenters': [
            {'uid':'cm1', 'cid':1, 'time':datetime(2016, 1, 9, 20, 9, 0)}
        ],
        'collectors': [
            {'uid':'cl1', 'cid':1, 'time':datetime(2016, 1, 9, 1, 9, 45)}
        ]
    }

    DB.db[a_col(tid)].insert(answer_info)

    t1 = datetime.now().replace(microsecond=0)
    # mock_upvote_time 在这里不起作用，故随便给一个值
    mock_upvote_time.return_value = t1
    mock_collect_time.side_effect = [
        datetime(2016,1,9,3,0,0),
        datetime(2016,1,9,4,0,0),
        datetime(2016,1,9,2,0,0),
    ]

    mock_answer = Mock(url=None, id=aid, creation_time=None, collect_num=1,
                       upvoters=deque([
                           Mock(id='up1'), Mock(id='up2'), Mock(id='up3')]),
                       comments=[Mock(uid='cm1', cid=1,
                                      creation_time=datetime(2016,1,9,20,9,0),
                                      author=Mock(id='cm1'))],
                       collections=[Mock(owner=Mock(id='cl1'), id=1)],
                       question=Mock(title='test question'), deleted=False)
    refresh = Mock()
    mock_question = Mock(id=qid)
    mock_author = Mock(id=author_id)

    def update_attrs():
        if refresh.call_count == 1:
            mock_answer.upvoters.appendleft(Mock(id='up4'))
            mock_answer.comments.append(Mock(cid=2, author=Mock(id='cm2'),
                                             creation_time=datetime(2016,1,9,21,1,0)))
            mock_answer.comments.append(Mock(cid=3, author=Mock(id='cm1'),
                                             creation_time=datetime(2016,1,9,21,2,0)))
            mock_answer.comments.append(Mock(cid=4, author=Mock(id='cm2'),
                                             creation_time=datetime(2016,1,9,21,4,0)))
            mock_answer.comments.append(Mock(cid=5, author=Mock(id='cm3'),
                                             creation_time=datetime(2016,1,9,23,5,0)))
            mock_answer.collections.append(Mock(id=2, owner=Mock(id='cl2')))
            mock_answer.collections.append(Mock(id=3, owner=Mock(id='cl3')))
            mock_answer.collections.append(Mock(id=4, owner=Mock(id='cl4')))
            mock_answer.collect_num += 3
        elif refresh.call_count == 2:
            mock_answer.deleted = True

    refresh.side_effect = update_attrs
    mock_answer.configure_mock(refresh=refresh, question=mock_question,
                               author=mock_author)

    task = FetchAnswerInfo(tid=tid, answer=mock_answer)
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)

    task.execute()
    answer_info['upvoters'].append({'uid':'up4', 'time':t1})
    answer_info['commenters'].extend([
        {'uid':'cm2', 'time':datetime(2016,1,9,21,1,0), 'cid':2},
        {'uid':'cm3', 'time':datetime(2016,1,9,23,5,0), 'cid':5}
    ])
    # 测试 collection 按时间排序
    answer_info['collectors'].extend([
        {'uid':'cl4', 'time':datetime(2016,1,9,2,0,0), 'cid':4},
        {'uid':'cl2', 'time':datetime(2016,1,9,3,0,0), 'cid':2},
        {'uid':'cl3', 'time':datetime(2016,1,9,4,0,0), 'cid':3}
    ])
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)

    task.execute()
    assert DB.find_one_answer(tid, aid) == None


def test_with_real_answer():
    # KLJ 大学怎么样？
    url = 'https://www.zhihu.com/question/37836315/answer/73732367'
    tid = '1234'
    client = zhihu.ZhihuClient('../cookies/zhuoyi.json')
    t = FetchAnswerInfo(tid, client.answer(url))
    t.execute()
    pprint(DB.db[a_col(tid)].find_one({'aid': '73732367'}))