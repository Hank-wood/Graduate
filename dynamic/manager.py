# coding: utf-8

"""
This is not ORM, it's (cache)manager, handles pure data but don't store them,
not aware of zhihu.XXX object
"""

import logging
from datetime import datetime
from collections import deque

import zhihu

from common import FETCH_FOLLOWEE, FETCH_FOLLOWER, topics, epoch
from db import DB
import huey_tasks

logger = logging.getLogger(__name__)


class QuestionManager:
    """
    在大部分情况下这个类的作用就是调用 db.py 提供的接口
    在某些的情况下用来缓存数据避免查询过多
    """

    latest_question_creation_time = {
        tid: None for tid in topics  # save qid of lastest question in a topic
    }

    @classmethod
    def set_latest(cls, tid, creation_time):
        """
        :param question: zhihu.Question object
        """
        cls.latest_question_creation_time[tid] = creation_time

    @classmethod
    def save_question(cls, tid, url, qid, time, asker, title):
        DB.save_question(tid, url, qid, time, asker, title)

    @classmethod
    def get_all_questions(cls, *args):
        return DB.get_all_questions(*args)

    @classmethod
    def get_all_questions_one_topic(cls, tid):
        return list(DB.get_questions(tid))

    @classmethod
    def remove_question(cls, tid, qid):
        DB.remove_question(tid, qid)

    @classmethod
    def add_question_follower(cls, tid, qid, new_followers):
        DB.add_question_follower(tid, qid, new_followers)

    @classmethod
    def get_question_follower(cls, tid, qid, limit=None):
        return set([f['uid'] for f in DB.get_question_follower(tid, qid, limit)])

    @classmethod
    def get_question_follower_num(cls, tid, qid):
        return DB.get_question_follower_num(tid, qid)

    @classmethod
    def get_question_attrs(cls, tid, qid, *args):
        """
        :return: [aid1, url1, title1]
        or       aid1
        """
        assert len(args) > 0
        doc = DB.get_question_attrs(tid, qid, *args)
        return_value = [doc[arg] for arg in args]
        return return_value if len(return_value) > 1 else return_value[0]

    @classmethod
    def set_question_inactive(cls, tid, qid):
        DB.set_question_inactive(tid, qid)


class AnswerManager:
    def __init__(self, tid, aid):
        self.tid = tid
        self.aid = aid
        answer_doc = DB.get_answer_affected_user_with_limit(tid, aid)
        if answer_doc:
            self.upvoters = deque([u['uid'] for u in answer_doc['upvoters']],
                                  maxlen=5)
            self.commenters = set(u['uid'] for u in answer_doc['commenters'])
            self.collectors = set(u['uid'] for u in answer_doc['collectors'])
            self.lastest_comment_time = answer_doc['commenters'][-1]['time'] \
                if len(answer_doc['commenters']) > 0 else epoch
            self.lastest_upvote_time = answer_doc['upvoters'][-1]['time'] \
                if len(answer_doc['upvoters']) > 0 else answer_doc['time']
        else:
            self.upvoters = deque()
            self.commenters = set()
            self.collectors = set()
            self.lastest_comment_time = epoch
            self.lastest_upvote_time = epoch

    def __eq__(self, other):
        return self.aid == other.aid

    def save_answer(self, qid, url, answerer, time):
        DB.save_answer(tid=self.tid, aid=self.aid, url=url, qid=qid,
                       time=time, answerer=answerer)
        huey_tasks.fetch_followers_followees(answerer, time, limit_to=FETCH_FOLLOWER)

    def sync_affected_users(self, new_upvoters=None, new_commenters=None,
                            new_collectors=None):
        """
        :param new_upvoters: [{'uid': uid1, 'time': timestamp1}, ...]
        :param new_commenters: [{'uid': uid1, 'time': timestamp1}, ...]
        :param new_collectors: [{'uid': uid1, 'time': timestamp1}, ...]
        :return:
        """
        if new_upvoters:
            # deque maxlen=5, 防止 upvoters 过多占用大量内存
            self.upvoters.extend([upvoter['uid'] for upvoter in new_upvoters])
            for upvoter in new_upvoters:
                huey_tasks.fetch_followers_followees(upvoter['uid'],
                                                     upvoter['time'])
            DB.add_upvoters(self.tid, self.aid, new_upvoters)

        if new_commenters:
            for commenter in new_commenters:
                self.commenters.add(commenter['uid'])
                huey_tasks.fetch_followers_followees(commenter['uid'],
                                                     commenter['time'],
                                                     limit_to=FETCH_FOLLOWEE)
            DB.add_commenters(self.tid, self.aid, new_commenters)
            self.lastest_comment_time = new_commenters[-1]['time']

        if new_collectors:
            for collector in new_collectors:
                self.collectors.add(collector['uid'])
                huey_tasks.fetch_followers_followees(collector['uid'],
                                                     collector['time'],
                                                     limit_to=FETCH_FOLLOWEE)
            DB.add_collectors(self.tid, self.aid, new_collectors)

    def remove_answer(self):
        DB.remove_answer(self.tid, self.aid)

    @classmethod
    def answer_exists(cls, tid, aid):
        return DB.answer_exists(tid, aid)

    @classmethod
    def get_question_answerer(cls, tid, qid):
        """
        :return: set of answerer ids
        """
        return set([a['answerer'] for a in DB.get_question_answerer(tid, qid)])

    @classmethod
    def get_question_answer_attrs(cls, tid, qid, *args):
        """
        :return: [(aid1, url1), (aid2, url2),...]
        or       [aid1, aid2, ...]
        """
        assert len(args) > 0
        cursor = DB.get_question_answer_attrs(tid, qid, *args)
        if len(args) > 1:
            return [[doc[arg] for arg in args] for doc in cursor]
        else:
            return [doc[args[0]] for doc in cursor]

    @classmethod
    def get_answer_affecter_num(cls, tid, aid):
        """ 获取 upvoter, commenter, collector 数量
        :return: (len_upvoters, len_commenters, len_collectors)
        """
        doc = DB.get_answer_affecter_num(tid, aid)
        return doc['up_count'], doc['com_count'], doc['col_count']


class User:
    def __init__(self):
        pass

    def save(self):
        pass
