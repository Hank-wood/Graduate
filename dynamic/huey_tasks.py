import logging
from functools import reduce, wraps
from pprint import pprint

import zhihu
from pymongo import MongoClient
from huey import RedisHuey
from requests.adapters import HTTPAdapter


huey = RedisHuey()
logger = logging.getLogger(__name__)
client = zhihu.ZhihuClient('../cookies/zhuoyi.json')
db = MongoClient('127.0.0.1', 27017).zhihu_data
user_coll = db.user


def replace_database(db_name=None):
    global user_coll
    if db_name is not None:
        user_coll = MongoClient('127.0.0.1', 27017).get_database(db_name).user


def _fetch_followers_followees(uid, dateime, db_name=None):
    prefix = 'https://www.zhihu.com/people/'
    user = client.author(prefix + uid)

    if user.followee_num < 500:
        _fetch_followees(user, dateime, db_name)

    if user.follower_num < 500:
        _fetch_followers(user, dateime, db_name)

    if user.followee_num >= 500 and user.follower_num >= 500:
        if user.followee_num < user.follower_num:
            _fetch_followees(user, dateime, db_name)
        else:
            _fetch_followers(user, dateime, db_name)


def _fetch_followers(user, datetime, db_name=None):
    replace_database(db_name)
    follower_num = user.follower_num
    doc = user_coll.find_one({'uid': user.id}, {'followers':1, '_id':0})
    if doc is None:
        # new user
        uids = [follower.id for follower in user.followers]
        assert len(uids) == follower_num
        user_coll.insert({
            'uid': user.id,
            "follower": [{
                'time': datetime,
                'uids': uids
            }]
        })
    else:
        # user exists
        try:
            if 'follower' in doc:
                old_followers = set(reduce(lambda x,y: x + y,
                                    [f['uids'] for f in doc['follower']]))
                old_follower_num = len(old_followers)
            else:
                old_followers = set()
                old_follower_num = 0
            # 至少有这么多新的 follower, 考虑取关则可能更多
            min_follower_increase = follower_num - old_follower_num
            if min_follower_increase <= 0:
                # 实际上这个时候也有可能有新follower,无视之,因为概率较小
                return

            new_followers = []
            for follower in user.followers:
                if follower.id not in old_followers:
                    new_followers.append(follower.id)
                elif min_follower_increase <= 0:
                    break
                min_follower_increase -= 1

            if new_followers:
                user_coll.update({'uid': user.id}, {
                    '$push': {
                        'follower': {
                            'time': datetime,
                            'uids': new_followers
                        }
                    }
                })
        except Exception as e:
            print("suspicious doc:")
            print(doc_follower)
            raise e


def _fetch_followees(user, datetime, db_name=None):
    replace_database(db_name)
    followee_num = user.followee_num
    doc = user_coll.find_one({'uid': user.id}, {'followees':1, '_id':0})
    if doc is None:
        # new user
        uids = [followee.id for followee in user.followees]
        assert len(uids) == followee_num
        user_coll.insert({
            'uid': user.id,
            "followee": [{
                'time': datetime,
                'uids': uids
            }]
        })
    else:
        # user exists
        try:
            if 'followee' in doc:
                old_followees = set(reduce(lambda x,y: x + y,
                                    [f['uids'] for f in doc['followee']]))
                old_followee_num = len(old_followees)
            else:
                old_followees = set()
                old_followee_num = 0
            # 至少有这么多新的 followee, 考虑取关则可能更多
            min_followee_increase = followee_num - old_followee_num
            if min_followee_increase <= 0:
                # 实际上这个时候也有可能有新followee,无视之,因为概率较小
                return

            new_followees = []
            for followee in user.followees:
                if followee.id not in old_followees:
                    new_followees.append(followee.id)
                elif min_followee_increase <= 0:
                    break
                min_followee_increase -= 1

            if new_followees:
                user_coll.update({'uid': user.id}, {
                    '$push': {
                        'followee': {
                            'time': datetime,
                            'uids': new_followees
                        }
                    }
                })
        except Exception as e:
            print("suspicious doc:")
            print(doc_followee)
            raise e


def remove_all_users(db_name=None):
    replace_database(db_name)
    user_coll.remove({})


def show_users(db_name=None):
    replace_database(db_name)
    logger.info(list(user_coll.find()))
    pprint(list(user_coll.find()))


def get_user(uid, db_name=None):
    replace_database(db_name)
    return user_coll.find_one({'uid': uid})


fetch_followers = huey.task()(_fetch_followers)
fetch_followees = huey.task()(_fetch_followees)
fetch_followers_followees = huey.task()(_fetch_followers_followees)
