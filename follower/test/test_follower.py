import time
from datetime import datetime

import requests

import follower


def setup_function(function):
    follower.remove_all_users()


def test_fetch_few():
    requests.get('http://127.0.0.1:5000/follower/aiwanxin')
    time.sleep(5)
    follower.show_users()


def test_fetch_many():
    time.sleep(5)
    requests.get('http://127.0.0.1:5000/follower/laike9m')
