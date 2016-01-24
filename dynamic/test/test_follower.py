import time
from datetime import datetime
# from

import requests
from pymongo import MongoClient

import huey_tasks
from huey_tasks import fetch_followers, show_users, remove_all_users
from utils import dict_equal


def setup_module(module):
    show_users()
    remove_all_users()


def test_fetch_few():
    fetch_followers('aiwanxin', datetime.now(), db_name='test')
    time.sleep(5)
    show_users('test')


def test_fetch_many():
    fetch_followers('laike9m', datetime.now(), db_name='test')
    time.sleep(5)
    show_users('test')
