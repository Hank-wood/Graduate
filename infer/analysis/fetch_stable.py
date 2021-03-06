"""
获取页面当前数据,供水军识别
使用 analysis 数据库
对于疑似水军的回答, 检测同问题下的至少另外两个回答, 这样能说明能否识别水军和非水军
传播特征作为第一步判断哪些答案可能是水军
和之前定期采集的不同在于
1. 要记录匿名用户点赞
2. 评论不去重
3. 不抓收藏, 因为收藏提供不了太多信息
"""

import re
import sys
from os import path
from pprint import pprint

import pymongo

import zhihu
from zhihu import ANONYMOUS
from client import client

db_name = 'analysis'

FETCH_FOLLOWER = 1
FETCH_FOLLOWEE = 2
db = pymongo.MongoClient('127.0.0.1', 27017).get_database(db_name)
water_q = db.water_q
water_a = db.water_a
sys.path.append(
    path.join(path.dirname(path.dirname(path.abspath(__file__))), 'dynamic'))
import huey_tasks
huey_tasks.replace_database(db_name)

qurl_pattern = re.compile(r'(.*)/answer')


def fetch_question_info(question_url):
    print(question_url)
    question = client.question(question_url)
    title = question.title
    followers = [{'uid': fo.id, 'time': None} for fo in question.followers
                 if fo is not ANONYMOUS]
    ctime = question.creation_time
    asker = question.author.id if question.author is not ANONYMOUS else ''
    qdoc = {
        'qid': str(question.id),
        'url': question_url,
        'time': ctime,
        'asker': asker,
        'follower': list(reversed(followers)),
        'title': title
    }
    pprint(qdoc)
    print("fetch " + asker)
    huey_tasks.fetch_followers_followees(asker, limit_to=FETCH_FOLLOWER)
    for follower in followers:
        print("fetch " + follower['uid'])
        huey_tasks.fetch_followers_followees(follower['uid'])
    water_q.update({'qid': qdoc['qid']}, qdoc, upsert=True)

    fetch_answer_info(question)


def fetch_answer_info(question):
    for answer in question.answers:
        author_id = answer.author.id if answer.author is not ANONYMOUS else ''
        adoc = {
            'url': answer.url,
            'aid': str(answer.id),
            'qid': str(answer.question.id),
            'answerer': author_id,
            'time': answer.creation_time,
            'collectors': []
        }
        # 'upvoters':
        upvoters = [up.id for up in answer.upvoters if up is not ANONYMOUS]
        commenters = [{
                      'uid': cm.author.id,
                      'time': cm.creation_time
                  } for cm in answer.comments if cm.author is not ANONYMOUS]
        adoc['upvoters'] = [{'uid': up, 'time': None} for up in upvoters]
        commenters.sort(key=lambda x: x['time'])
        adoc['commenters'] = commenters
        pprint(adoc)

        # fetch follower/followee
        print(adoc['answerer'])
        huey_tasks.fetch_followers_followees(adoc['answerer'])
        for upvoter in upvoters:
            print('fetch ' + upvoter)
            huey_tasks.fetch_followers_followees(upvoter)
        for commenter in commenters:
            print('fetch ' + commenter['uid'])
            huey_tasks.fetch_followers_followees(commenter['uid'], limit_to=FETCH_FOLLOWEE)

        # 入库
        water_a.update({'aid': adoc['aid']}, adoc, upsert=True)


def fetch_single_answer(url):
    answer = client.answer(url)
    author_id = answer.author.id if answer.author is not ANONYMOUS else ''
    adoc = {
        'url': answer.url,
        'aid': str(answer.id),
        'qid': str(answer.question.id),
        'answerer': author_id,
        'time': answer.creation_time,
        'collectors': []
    }
    # 'upvoters':
    upvoters = [up.id for up in answer.upvoters if up is not ANONYMOUS]
    commenters = [{
                      'uid': cm.author.id,
                      'time': cm.creation_time
                  } for cm in answer.comments if cm.author is not ANONYMOUS]
    adoc['upvoters'] = [{'uid': up, 'time': None} for up in upvoters]
    commenters.sort(key=lambda x: x['time'])
    adoc['commenters'] = commenters
    pprint(adoc)

    # fetch follower/followee
    print(adoc['answerer'])
    huey_tasks.fetch_followers_followees(adoc['answerer'])
    for upvoter in upvoters:
        print('fetch ' + upvoter)
        huey_tasks.fetch_followers_followees(upvoter)
    for commenter in commenters:
        print('fetch ' + commenter['uid'])
        huey_tasks.fetch_followers_followees(commenter['uid'], limit_to=FETCH_FOLLOWEE)

    # 入库
    water_a.update({'aid': adoc['aid']}, adoc, upsert=True)

if __name__ == '__main__':
    # fetch_question_info('https://www.zhihu.com/question/42985161')
    # fetch_question_info('https://www.zhihu.com/question/35107886')
    fetch_single_answer('https://www.zhihu.com/question/35107886/answer/61219684')