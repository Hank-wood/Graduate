import follower
from datetime import datetime


def setup_function(function):
    follower.remove_all_users()


def test_fetch_few():
    now = datetime.now()
    follower.fetch_followers('aiwanxin', now)
    follower.show_users()


def test_fetch_many():
    now = datetime.now()
    follower.fetch_followers('laike9m', now)
