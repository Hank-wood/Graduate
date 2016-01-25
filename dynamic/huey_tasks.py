import logging

import zhihu
from pymongo import MongoClient
from huey import RedisHuey
from requests.adapters import HTTPAdapter


huey = RedisHuey()
logger = logging.getLogger(__name__)
client = zhihu.ZhihuClient('../cookies/zhuoyi.json')
db = MongoClient('127.0.0.1', 27017).zhihu_data
user_coll = db.user


def _fetch_followers(uid, datetime, db_name=None):
    global user_coll
    if db_name is not None:
        user_coll = MongoClient('127.0.0.1', 27017).get_database(db_name).user

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
        # user exists
        old_followers = set(reduce(lambda x,y:x.extend(y),
                                   [f['uids'] for f in doc['follower']]))
        old_follower_num = len(old_followers)
        # 至少有这么多新的 follower, 考虑取关则可能更多
        min_follower_increase = user.follower_num - old_follower_num
        new_followers = []
        for follower in user.followers:
            if follower not in old_followers:
                new_followers.append(follower.id)
            elif min_follower_increase > 0:
                pass
            else:
                break
            min_follower_increase -= 1

        user_coll.update({'uid': uid}, {
            '$push': {
                'follower': {
                    'time': datetime,
                    'uids': new_followers
                }
            }
        })


def fetch_many_followers(uid):
    user_coll.insert({
        'uid': uid,
        "follower": []
    })


def remove_all_users():
    user_coll.remove({})


def show_users(db_name=None):
    global user_coll
    if db_name is not None:
        user_coll = MongoClient('127.0.0.1', 27017).get_database(db_name).user
    logger.info(list(user_coll.find()))
    print(list(user_coll.find()))


fetch_followers = huey.task()(_fetch_followers)
