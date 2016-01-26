# coding: utf-8

"""
This is not ORM, it's (cache)manager, handles pure data but don't store them,
not aware of zhihu.XXX object
"""

import logging
from datetime import datetime

import ezcf
import zhihu

from config.dynamic_config import topics
from db import DB

logger = logging.getLogger(__name__)


class QuestionManager:
    """
    在大部分情况下这个类的作用就是调用 db.py 提供的接口
    在某些的情况下用来缓存数据避免查询过多
    """

    latest_question = {
        tid: None for tid in topics  # save qid of lastest question in a topic
    }

    @classmethod
    def is_latest(cls, tid, question):
        if cls.latest_question[tid]:
            return cls.latest_question[tid] == question.id
        else:
            doc = DB.find_latest_question(tid)
            if doc:
                cls.latest_question[tid] = doc['qid']
                return doc['qid'] == question.id
            else:
                # 第一次执行, 外部 set_latest 不会调用, 在这里初始化
                cls.set_latest(tid, question)
                return True

    @classmethod
    def set_latest(cls, tid, question):
        """
        :param question: zhihu.Question object
        """
        logger.debug("Set latest question of %s to %s" % (topics[tid], question.id))
        cls.latest_question[tid] = question.id

    @classmethod
    def save(cls, tid, url, qid, time, asker, title):
        DB.save_question(tid, url, qid, time, asker, title)

    @classmethod
    def get_all_questions(cls):
        return DB.get_all_questions()

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
    def get_question_follower(cls, tid, qid):
        return set(DB.get_question_follower(tid, qid))


class AnswerManager:
    def __init__(self, tid, aid):
        self.tid = tid
        self.aid = aid
        self.new_answer = True
        answer_doc = DB.find_one_answer(tid, aid)
        if answer_doc:
            self.new_answer = False
            self.upvoters = set(u['uid'] for u in answer_doc['upvoters'])
            self.commenters = set(u['uid'] for u in answer_doc['commenters'])
            self.collectors = set(u['uid'] for u in answer_doc['collectors'])
            if answer_doc['commenters']:
                self.lastest_comment_time = answer_doc['commenters'][-1]['time']
            else:
                self.lastest_comment_time = datetime(1970, 1, 1, 0, 0, 0)
        else:
            self.upvoters = set()
            self.commenters = set()
            self.collectors = set()
            self.lastest_comment_time = datetime(1970, 1, 1, 0, 0, 0)

    def __eq__(self, other):
        return self.aid == other.aid

    def sync_basic_info(self, qid, url, answerer, time):
        if self.new_answer:
            DB.save_answer(tid=self.tid, aid=self.aid, url=url, qid=qid,
                           time=time, answerer=answerer)

    def sync_affected_users(self, new_upvoters=None, new_commenters=None,
                            new_collectors=None):
        """
        :param new_upvoters: [{'uid': uid1, 'time': timestamp1}, ...]
        :param new_commenters: [{'uid': uid1, 'time': timestamp1}, ...]
        :param new_collectors: [{'uid': uid1, 'time': timestamp1}, ...]
        :return:
        """
        if new_upvoters:
            for upvoter in new_upvoters:
                self.upvoters.add(upvoter['uid'])
            DB.add_upvoters(self.tid, self.aid, new_upvoters)

        if new_commenters:
            for commenter in new_commenters:
                self.commenters.add(commenter['uid'])
            DB.add_commenters(self.tid, self.aid, new_commenters)
            self.lastest_comment_time = new_commenters[-1]['time']

        if new_collectors:
            for collector in new_collectors:
                self.collectors.add(collector['uid'])
            DB.add_collectors(self.tid, self.aid, new_collectors)

    def remove_answer(self):
        DB.remove_answer(self.tid, self.aid)


class User:
    def __init__(self):
        pass

    def save(self):
        pass
