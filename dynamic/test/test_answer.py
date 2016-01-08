import os
import time
import json
from datetime import datetime, timedelta
from collections import deque
from unittest.mock import patch, Mock

from pymongo import MongoClient
import pytest

from model import AnswerManager
from db import DB
from task import FetchAnswerInfo
from utils import *
from common import *


db = MongoClient('127.0.0.1', 27017).test


def setup_function(function):
    DB.db = db  # replace db with test db


def teardown_function(function):
    for collection_name in db.collection_names():
        if 'system' not in collection_name:
            db[collection_name].drop()


@patch('task.FetchAnswerInfo.get_upvote_time')
@patch('task.FetchAnswerInfo.get_comment_time')
@patch('task.FetchAnswerInfo.get_collect_time')
def test_fetch_answers_without_previous_data(mock_upvote_time,
                                             mock_comment_time,
                                             mock_collect_time):
    aid = '111111'

    # mongodb can't store microsecond
    t1 = datetime.now().replace(microsecond=0)
    t2 = t1+timedelta(1)
    t3 = t2+timedelta(1)
    mock_upvote_time.side_effect = [t1, t2, t3]
    mock_comment_time.side_effect = [t1, t2, t3]
    mock_collect_time.side_effect = [t1, t2, t3]

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
            mock_answer.comments.appendleft(Mock(cid=1, author=Mock(id='cm1')))
        elif refresh.call_count == 3:
            mock_answer.upvoters.appendleft(Mock(id='up3'))
            mock_answer.comments.appendleft(Mock(cid=2, author=Mock(id='cm2')))
            mock_answer.collections.appendleft(Mock(id=2, onwer=Mock(id='cl1')))
            mock_answer.collect_num += 1

    refresh.side_effect = update_attrs
    mock_answer.configure_mock(refresh=refresh, question=mock_question,
                               author=mock_author)

    tid = '123456'
    task = FetchAnswerInfo(tid=tid, answer=mock_answer)

    assert dict_equal(DB.find_one_answer(tid, aid), {
        'topic': tid, 'aid': aid, 'qid': 'question_id', 'answerer': 'author_id',
        'upvoters': [], 'commenters': [], 'collectors': []
    })

    task.execute()
    assert dict_equal(DB.find_one_answer(tid, aid), {
        'topic': tid, 'aid': aid, 'qid': 'question_id', 'answerer': 'author_id',
        'upvoters': [{'uid':'up1', 'time':t1}], 'commenters': [], 'collectors': []
    })

    # TODO: more tests


def test_fetch_answers_with_previous_data():
    pass
