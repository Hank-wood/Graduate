import os
import time
import json
from datetime import datetime
from collections import deque
from unittest.mock import patch, PropertyMock, Mock

from pymongo import MongoClient
import pytest

from model import AnswerModel
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


@patch('task.FetchAnswerInfo.get_upvote_time', new=lambda x,y: datetime.now())
@patch('task.FetchAnswerInfo.get_comment_time', new=lambda x: datetime.now())
@patch('task.FetchAnswerInfo.get_collect_time', new=lambda x,y: datetime.now())
def test_fetch_answers_without_previous_data():
    mock_answer = Mock(url=None, aid='1', qid=None, answerer=None, time=None,
                       upvoters=deque(), comments=deque(), collections=deque())
    refresh=Mock()

    def update_attrs():
        if refresh.call_count == 1:
            pass
        elif refresh.call_count == 2:
            mock_answer.upvoters.appendleft(Mock(id=1))
        elif refresh.call_count == 3:
            mock_answer.upvoters.appendleft(Mock(id=2))
            mock_answer.comments.appendleft(Mock(cid=1, author=Mock(id=3)))
        elif refresh.call_count == 4:
            mock_answer.upvoters.appendleft(Mock(id=3))
            mock_answer.comments.appendleft(Mock(cid=2, author=Mock(id=4)))
            mock_answer.collections.appendleft(Mock(id=2, onwer=Mock(id=5)))

    refresh.side_effect = update_attrs
    mock_answer.configure_mock(refresh=refresh)

    # answer.aid, refresh(), upvoters, comments, collections
    # upvoter.id, comment.cid, comment.author.id, collection.id,
    # collection.onwer.id
    task = FetchAnswerInfo(tid='123456', answer=mock_answer)
    mock_answer.refresh()



def test_fetch_answers_with_previous_data():
    pass
