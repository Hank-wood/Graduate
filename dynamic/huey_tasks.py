import sys
import logging
import os
import json
import logging.handlers
from functools import reduce, wraps
from pprint import pprint

import zhihu
from pymongo import MongoClient
from huey import RedisHuey
from requests.adapters import HTTPAdapter
from zhihu import ANONYMOUS

from common import FETCH_FOLLOWEE, FETCH_FOLLOWER, FetchTypeError,\
    logging_config_file, smtp_config_file, logging_dir
from client_pool import get_client
from utils import config_smtp_handler


huey = RedisHuey()
logger = logging.getLogger('huey.consumer')
logger2 = logging.getLogger('huey.consumer.Worker')
logger2.setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

if os.path.isfile(logging_config_file):
    with open(logging_config_file, 'rt') as f:
        config = json.load(f)
        mail_handler_cfg = config['handlers']['mail_handler']
        smtp_handler = logging.handlers.SMTPHandler(
            mailhost=(mail_handler_cfg['mailhost'], 25),
            fromaddr=mail_handler_cfg['fromaddr'],
            toaddrs=mail_handler_cfg['toaddrs'],
            subject="Huey Error")
        # level=critical, 防止每次 retry 的时候都发邮件
        # 只有最后一次 attribute error retry 和未知错误才发邮件
        smtp_handler.setLevel(logging.CRITICAL)
        logger.addHandler(smtp_handler)
        config_smtp_handler(smtp_handler)

db = MongoClient('127.0.0.1', 27017).zhihu_data
user_coll = db.user

# 1. 防止两个线程同时抓取一个用户
# 2. 保证在 retries 用完时才输出错误
# {uid: {'retries': 3, 'running': True}
task_info = {}


def replace_database(db_name=None):
    global user_coll
    if db_name is not None:
        user_coll = MongoClient('127.0.0.1', 27017).get_database(db_name).user


def _fetch_followers_followees(uid, datetime, db_name=None, limit_to=None):
    if uid == '':
        return  # 匿名用户

    if uid in task_info:
        if task_info[uid]['running']:
            logger.info("重复用户:" + uid)
            return
        else:
            task_info[uid]['running'] = True
    else:
        task_info[uid] = {'retries': 3, 'running': True}

    logger.info("fetch: " + uid)
    url = 'https://www.zhihu.com/people/' + uid
    user = get_client().author(url)
    user._session.mount(url, HTTPAdapter(pool_connections=1, max_retries=3))
    # 如果有需要, 把/node/ProfileFollowersListV2和/node/ProfileFolloweesListV2也mount

    try:
        if limit_to is None:
            if user.followee_num < 500:
                _fetch_followees(user, datetime, db_name)

            if user.follower_num < 500:
                _fetch_followers(user, datetime, db_name)

            if user.followee_num >= 500 and user.follower_num >= 500:
                if user.followee_num < user.follower_num:
                    _fetch_followees(user, datetime, db_name)
                else:
                    _fetch_followers(user, datetime, db_name)
        elif limit_to == FETCH_FOLLOWER:
            _fetch_followers(user, datetime, db_name)
        elif limit_to == FETCH_FOLLOWEE:
            _fetch_followees(user, datetime, db_name)
        else:
            raise FetchTypeError("No such type: " + str(limit_to))
    except AttributeError as e:
        # dump error user profile html
        html = user.soup.prettify("utf-8")
        with open(os.path.join(logging_dir, user.id), "wb") as file:
            file.write(html)
        if task_info[uid]['retries'] == 0:
            del task_info[uid]  # remove if task failed completely
            logger.critical(user.url, exc_info=True)
        else:
            task_info[uid]['retries'] -= 1
            task_info[uid]['running'] = False
        raise e  # reraise so that retry can fire
    except Exception as e:
        del task_info[uid]  # remove if task failed completely
        logger.critical(user.url, exc_info=True)
        raise e.with_traceback(sys.exc_info()[2])
    else:
        del task_info[uid]  # remove if task succeed

    # 防止 adapters 无限增长
    try:
        del user._session.adapters[url]
    except KeyError:
        pass


def _fetch_followers(user, datetime, db_name=None):
    replace_database(db_name)
    follower_num = user.follower_num
    if follower_num > 2000:
        return
    doc = user_coll.find_one({'uid': user.id}, {'follower':1, '_id':0})
    if doc is None:
        # new user
        uids = [follower.id for follower in user.followers if follower is not ANONYMOUS]
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
                if follower is ANONYMOUS:
                    min_follower_increase -= 1
                else:
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
    if followee_num > 2000:
        return
    doc = user_coll.find_one({'uid': user.id}, {'followee':1, '_id':0})
    if doc is None:
        # new user
        uids = [followee.id for followee in user.followees if followee is not ANONYMOUS]
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
                if followee is ANONYMOUS:
                    min_followee_increase -= 1
                else:
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


fetch_followers = huey.task(retries=3, retry_delay=2)(_fetch_followers)
fetch_followees = huey.task(retries=3, retry_delay=2)(_fetch_followees)
fetch_followers_followees = huey.task(retries=3, retry_delay=2)(_fetch_followers_followees)
