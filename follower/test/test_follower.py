import follower
from datetime import datetime


def test_fetch_few():
    now = datetime.now()
    follower.fetch_followers('aiwanxin', now)