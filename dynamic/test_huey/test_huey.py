"""
在启动了 huey_consumer 的情况下测试
"""

from functools import partial
from datetime import datetime
from huey_tasks import fetch_followers_followees, remove_all_users, show_users,\
                        get_user

import pytest


fetch_followers_followees = partial(fetch_followers_followees, db_name='test')
remove_all_users = partial(remove_all_users, db_name='test')
show_users = partial(show_users, db_name='test')
get_user = partial(get_user, db_name='test')


def teardown_function(function):
    remove_all_users()


def test_fetch_few2():
    fetch_followers_followees('aiwanxin', datetime.now())
    show_users()
    doc = get_user('aiwanxin')
    assert len(doc['follower'][0]['uids']) >= 32
    assert len(doc['followee'][0]['uids']) >= 44


def test_smtp_handler():
    # should send error alert email
    fetch_followers_followees(1, None)
