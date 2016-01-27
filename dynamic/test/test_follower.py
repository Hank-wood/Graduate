import time
from datetime import datetime, timedelta
from functools import partial
from unittest.mock import Mock, patch, PropertyMock

import requests
import pytest
import zhihu
from pymongo import MongoClient

import huey_tasks
from huey_tasks import _fetch_followers, _fetch_followees, show_users,\
    remove_all_users, get_user, _fetch_followers_followees
from utils import dict_equal


_fetch_followers_followees = partial(_fetch_followers_followees, db_name='test')
_fetch_followees = partial(_fetch_followees, db_name='test')
_fetch_followers = partial(_fetch_followers, db_name='test')
get_user = partial(get_user, db_name='test')
remove_all_users = partial(remove_all_users, db_name='test')
show_users = partial(show_users, db_name='test')
client = zhihu.ZhihuClient('../cookies/zhuoyi.json')
laike9m = client.author('https://www.zhihu.com/people/laike9m')
aiwanxin = client.author('https://www.zhihu.com/people/aiwanxin')


def teardown_function(function):
    remove_all_users()


# @pytest.mark.skipif(True, reason='')
def test_fetch_few():
    _fetch_followers(aiwanxin, datetime.now())
    _fetch_followees(aiwanxin, datetime.now())
    show_users()
    doc = get_user('aiwanxin')
    assert len(doc['follower'][0]['uids']) >= 32
    assert len(doc['followee'][0]['uids']) >= 44


# @pytest.mark.skipif(True, reason='')
def test_fetch_few2():
    _fetch_followers_followees('aiwanxin', datetime.now())
    show_users()
    doc = get_user('aiwanxin')
    assert len(doc['follower'][0]['uids']) >= 32
    assert len(doc['followee'][0]['uids']) >= 44


# @pytest.mark.skipif(True, reason='')
def test_fetch_many():
    # 多follower, 少followee
    _fetch_followers_followees('laike9m', datetime.now())
    doc = get_user('laike9m')
    assert 'follower' not in doc
    assert len(doc['followee'][0]['uids']) >= 332

    # 多followee, 少follower
    _fetch_followers_followees('yang-de-33-3', datetime.now())
    doc = get_user('yang-de-33-3')
    assert 'followee' not in doc
    assert len(doc['follower'][0]['uids']) >= 15

    show_users()


# @pytest.mark.skipif(True, reason='')
@patch('huey_tasks.zhihu.Author.follower_num', new_callable=PropertyMock)
@patch('huey_tasks.zhihu.Author.followers', new_callable=PropertyMock)
@patch('huey_tasks.zhihu.Author.followee_num', new_callable=PropertyMock)
@patch('huey_tasks.zhihu.Author.followees', new_callable=PropertyMock)
def test_fetch_many2(ees, ee_num, ers, er_num):
    # 测试 follower 和 followee 均超过 500 的情况
    # follower_num < followwee_num
    er_num.return_value = 501
    ers.return_value  = [Mock(id='uid'+str(i)) for i in range(501)]
    ee_num.return_value  = 502
    ees.return_value = [Mock(id='uid'+str(i)) for i in range(502)]
    _fetch_followers_followees('test_user', datetime.now())
    doc = get_user('test_user')
    assert 'followee' not in doc
    assert len(doc['follower'][0]['uids']) == 501

    # follower_num > followwee_num
    er_num.return_value = 502
    ers.return_value  = [Mock(id='uid'+str(i)) for i in range(502)]
    ee_num.return_value  = 501
    ees.return_value = [Mock(id='uid'+str(i)) for i in range(501)]
    _fetch_followers_followees('test_user2', datetime.now())
    doc = get_user('test_user2')
    assert 'follower' not in doc
    assert len(doc['followee'][0]['uids']) == 501


#@pytest.mark.skipif(True, reason='')
@patch('huey_tasks.zhihu.Author.follower_num', new_callable=PropertyMock)
@patch('huey_tasks.zhihu.Author.followers', new_callable=PropertyMock)
def test_fetch_increased_followers(ers, er_num):
    ers.side_effect = [
        [Mock(id='a'), Mock(id='b')],
        [Mock(id='c'), Mock(id='a'), Mock(id='b')],
        [Mock(id='e'), Mock(id='d'), Mock(id='c'), Mock(id='b')], # a unfollowed
    ]
    er_num.side_effect = [2, 2, 3, 4]
    now = datetime.now()
    _fetch_followers(laike9m, now)
    doc = get_user('laike9m')
    assert len(doc['follower']) == 1
    assert doc['follower'][0]['uids'] == ['a', 'b']

    _fetch_followers(laike9m, now + timedelta(seconds=1))
    doc = get_user('laike9m')
    assert len(doc['follower']) == 1
    assert doc['follower'][0]['uids'] == ['a', 'b']

    _fetch_followers(laike9m, now + timedelta(seconds=2))
    doc = get_user('laike9m')
    assert len(doc['follower']) == 2
    assert doc['follower'][0]['uids'] == ['a', 'b']
    assert doc['follower'][1]['uids'] == ['c']

    _fetch_followers(laike9m, now + timedelta(seconds=3))
    doc = get_user('laike9m')
    assert len(doc['follower']) == 3
    assert doc['follower'][0]['uids'] == ['a', 'b']
    assert doc['follower'][1]['uids'] == ['c']
    assert doc['follower'][2]['uids'] == ['e', 'd']


#@pytest.mark.skipif(True, reason='')
@patch('huey_tasks.zhihu.Author.followee_num', new_callable=PropertyMock)
@patch('huey_tasks.zhihu.Author.followees', new_callable=PropertyMock)
def test_increased_followees(ees, ee_num):
    ees.side_effect = [
        [Mock(id='a'), Mock(id='b')],
        [Mock(id='c'), Mock(id='a'), Mock(id='b')],
        [Mock(id='e'), Mock(id='d'), Mock(id='c'), Mock(id='b')], # a unfollowed
    ]
    ee_num.side_effect = [2, 2, 3, 4]
    now = datetime.now()
    _fetch_followees(laike9m, now)
    doc = get_user('laike9m')
    assert len(doc['followee']) == 1
    assert doc['followee'][0]['uids'] == ['a', 'b']

    _fetch_followees(laike9m, now + timedelta(seconds=1))
    doc = get_user('laike9m')
    assert len(doc['followee']) == 1
    assert doc['followee'][0]['uids'] == ['a', 'b']

    _fetch_followees(laike9m, now + timedelta(seconds=2))
    doc = get_user('laike9m')
    assert len(doc['followee']) == 2
    assert doc['followee'][0]['uids'] == ['a', 'b']
    assert doc['followee'][1]['uids'] == ['c']

    _fetch_followees(laike9m, now + timedelta(seconds=3))
    doc = get_user('laike9m')
    assert len(doc['followee']) == 3
    assert doc['followee'][0]['uids'] == ['a', 'b']
    assert doc['followee'][1]['uids'] == ['c']
    assert doc['followee'][2]['uids'] == ['e', 'd']
