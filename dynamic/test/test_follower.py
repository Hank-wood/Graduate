import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, PropertyMock

import requests
import pytest
from pymongo import MongoClient

import huey_tasks
from huey_tasks import _fetch_followers, show_users, remove_all_users, get_user
from utils import dict_equal



def setup_function(function):
    remove_all_users(db_name='test')


@pytest.mark.skipif(True, reason='')
def test_fetch_few():
    _fetch_followers('aiwanxin', datetime.now(), db_name='test')
    time.sleep(5)
    show_users('test')

@pytest.mark.skipif(True, reason='')
def test_fetch_many():
    _fetch_followers('laike9m', datetime.now(), db_name='test')
    time.sleep(5)
    show_users('test')


@patch('huey_tasks.zhihu.Author.follower_num', new_callable=PropertyMock)
@patch('huey_tasks.zhihu.Author.followers', new_callable=PropertyMock)
def test_fetch_increased_followers(mock_followers, mock_follower_num):
    mock_followers.side_effect = [
        [Mock(id='a'), Mock(id='b')],
        [Mock(id='c'), Mock(id='a'), Mock(id='b')],
        [Mock(id='e'), Mock(id='d'), Mock(id='c'), Mock(id='b')], # a unfollowed
    ]

    mock_follower_num.side_effect = [2,2,3,4]
    now = datetime.now()
    _fetch_followers('laike9m', now, db_name='test')
    doc = get_user('laike9m', db_name='test')
    assert len(doc['follower']) == 1
    assert doc['follower'][0]['uids'] == ['a', 'b']

    _fetch_followers('laike9m', now + timedelta(seconds=1), db_name='test')
    doc = get_user('laike9m', db_name='test')
    assert len(doc['follower']) == 1
    assert doc['follower'][0]['uids'] == ['a', 'b']

    _fetch_followers('laike9m', now + timedelta(seconds=2), db_name='test')
    doc = get_user('laike9m', db_name='test')
    assert len(doc['follower']) == 2
    assert doc['follower'][0]['uids'] == ['a', 'b']
    assert doc['follower'][1]['uids'] == ['c']

    _fetch_followers('laike9m', now + timedelta(seconds=3), db_name='test')
    doc = get_user('laike9m', db_name='test')
    assert len(doc['follower']) == 3
    assert doc['follower'][0]['uids'] == ['a', 'b']
    assert doc['follower'][1]['uids'] == ['c']
    assert doc['follower'][2]['uids'] == ['e', 'd']

