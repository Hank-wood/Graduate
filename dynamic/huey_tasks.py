import logging

import zhihu
from pymongo import MongoClient
from huey import RedisHuey
from requests.adapters import HTTPAdapter


huey = RedisHuey()
logger = logging.getLogger(__name__)
client = zhihu.ZhihuClient('../cookies/zhuoyi.json')
# 因为已经 run 起来了,所以没法改变 db 值
db = MongoClient('127.0.0.1', 27017).zhihu_data
user_coll = db.user


@huey.task()
def fetch_followers(uid, datetime, db):
    prefix = 'https://www.zhihu.com/people/'
    user = client.author(prefix + uid)
    uids = []

    doc = user_coll.find_one({'uid': uid})
    if doc is None:
        # new user
        if user.follower_num > 1000:
            fetch_many_followers(uid)
        else:
            for follower in user.followers:
                uids.append(follower.id)

            assert len(uids) == user.follower_num
            user_coll.insert({
                'uid': uid,
                "follower": [{
                    'time': datetime,
                    'uids': uids
                }]
            })
            print(uids)
    else:
        # TODO: insert newly added followers
        pass


def fetch_many_followers(uid):
    user_coll.insert({
        'uid': uid,
        "follower": []
    })


def remove_all_users():
    user_coll.remove({})


def show_users():
    logger.info(list(user_coll.find()))
    print(list(user_coll.find()))

