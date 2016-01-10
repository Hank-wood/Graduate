import os
import time
import json
from datetime import datetime, timedelta, time
from collections import deque
from unittest.mock import patch, Mock

from pymongo import MongoClient
import pytest

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


def teardown_function(function):
    for collection_name in DB.db.collection_names():
        if 'system' not in collection_name:
            DB.db[collection_name].drop()


@patch('task.FetchAnswerInfo.get_upvote_time')
@patch('task.FetchAnswerInfo.get_collect_time')
def test_fetch_answers_without_previous_data(mock_upvote_time,
                                             mock_collect_time):
    # mongodb can't store microsecond
    t1 = datetime.now().replace(microsecond=0)
    mock_upvote_time.side_effect = mock_collect_time.side_effect \
                                 = [t1+timedelta(i) for i in range(10)]

    mock_answer = Mock(url=None, id=aid, time=None, collect_num=0,
                       upvoters=deque(),
                       comments=deque(), collections=deque())
    refresh = Mock()
    mock_question = Mock(id='question_id')
    mock_author = Mock(id='author_id')

    def update_attrs():
        if refresh.call_count == 1:
            mock_answer.upvoters.appendleft(Mock(id='up1'))
        elif refresh.call_count == 2:
            mock_answer.upvoters.appendleft(Mock(id='up2'))
            mock_answer.comments.appendleft(Mock(cid=1, author=Mock(id='cm1'),
                                                 time_string='12:01'))
        elif refresh.call_count == 3:
            mock_answer.upvoters.appendleft(Mock(id='up3'))
            mock_answer.comments.appendleft(Mock(cid=2, author=Mock(id='cm2'),
                                                 time_string='12:02'))
            mock_answer.collections.appendleft(Mock(id=1, owner=Mock(id='cl1')))
            mock_answer.collect_num += 1
        elif refresh.call_count == 4:
            mock_answer.comments.appendleft(Mock(cid=3, author=Mock(id='cm1'),
                                                 time_string='12:03'))
        elif refresh.call_count == 5:
            mock_answer.comments.appendleft(Mock(cid=4, author=Mock(id='cm3'),
                                                 time_string='12:04'))
            mock_answer.comments.appendleft(Mock(cid=5, author=Mock(id='cm1'),
                                                 time_string='12:05'))

    refresh.side_effect = update_attrs
    mock_answer.configure_mock(refresh=refresh, question=mock_question,
                               author=mock_author)

    task = FetchAnswerInfo(tid=tid, answer=mock_answer)
    answer_info = {
        'topic': tid, 'aid': aid, 'qid': 'question_id', 'answerer': 'author_id',
        'upvoters': [], 'commenters': [], 'collectors': []
    }
    day = datetime.now().date()
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)

    task.execute()
    answer_info['upvoters'].append({'uid':'up1', 'time':t1})
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)

    task.execute()
    answer_info['upvoters'].append({'uid':'up2', 'time':t1+timedelta(1)})
    answer_info['commenters'].append({'uid':'cm1', 'cid':1,
                                      'time':datetime.combine(day, time(12,1))})
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)

    task.execute()
    answer_info['upvoters'].append({'uid':'up3', 'time':t1+timedelta(2)})
    answer_info['commenters'].append({'uid':'cm2', 'cid':2,
                                      'time':datetime.combine(day, time(12,2))})
    answer_info['collectors'].append({'uid':'cl1', 'time':t1, 'cid':1})
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)

    # test adding comment posted by same person
    task.execute()
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)

    task.execute()
    answer_info['commenters'].append({'uid':'cm3', 'cid':4,
                                     'time':datetime.combine(day, time(12,4))})
    assert dict_equal(DB.find_one_answer(tid, aid), answer_info)


def test_fetch_answers_with_previous_data():
    pass
