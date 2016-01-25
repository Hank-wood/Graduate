import time
from datetime import datetime
from unittest.mock import Mock, patch

import requests
from pymongo import MongoClient

import huey_tasks
from huey_tasks import _fetch_followers, show_users, remove_all_users, _function
from utils import dict_equal


def setup_module(module):
    show_users()
    remove_all_users()


def test_fetch_few():
    _fetch_followers('aiwanxin', datetime.now(), db_name='test')
    time.sleep(5)
    show_users('test')


def test_fetch_many():
    _fetch_followers('laike9m', datetime.now(), db_name='test')
    time.sleep(5)
    show_users('test')
