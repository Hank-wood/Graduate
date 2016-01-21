from pprint import pprint

import zhihu
from pymongo import MongoClient


client = zhihu.ZhihuClient('../cookies/zhuoyi.json')
db = MongoClient('127.0.0.1', 27017).zhihu_data
user_coll = db.user


def fetch_followers(uid, datetime):
    prefix = 'https://www.zhihu.com/people/'
    user = client.author(prefix + uid)
    uids = []

    if user.follower_num > 1000:
        fetch_many_followers(uid)
    else:
        for follower in user.followers:
            uids.append(follower.id)
        pprint(uids)
        assert len(uids) == user.follower_num


def fetch_many_followers(uid):
    pass