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


class QuestionModel:

    latest_question = {
        tid: None for tid in topics  # for cache
    }

    def __init__(self, tid, url=None, qid=None, asker=None, time=None, title=None,
                 question=None):
        """
        :param tid: fetched from which topic
        :param url: answer url
        :param qid: question id
        :param asker: question author id
        :param time: time question is raised
        :param title: question title
        :param question: zhihu.Question object
        """
        self.tid = tid
        if question:
            try:
                self.url = question.url
                self.qid = question.id
                if self.qid == '':
                    pass
                self.time = question.creation_time
                self.title = question.title
                if question.author:
                    self.asker = question.author.id
                else:
                    self.asker = ''  # 匿名用户, TODO: zhihu-py3增加ANONYMOUS常量
            except AttributeError:
                logging.exception("Error init QuestionModel\n")
        else:
            self.url = url
            self.qid = qid
            self.time = time
            self.asker = asker
            self.title = title
        self.answers = []

    @classmethod
    def is_latest(cls, tid, question):
        if cls.latest_question[tid]:
            return cls.latest_question[tid].qid == question.id
        else:
            doc = DB.find_latest_question(tid)
            if doc:
                cls.latest_question[tid] = cls.doc2question(doc)
                logger.debug("latest: " + str(cls.latest_question[tid]))
                return doc['qid'] == question.id
            else:
                # 第一次执行, 外部 set_latest 不会调用, 在这里初始化
                cls.set_latest(tid, question)
                logger.debug("latest: " + str(cls.latest_question[tid]))
                return True

    @classmethod
    def set_latest(cls, tid, question):
        """
        :param question: zhihu.Question object
        """
        logger.debug("Set latest question of %s to %s" % (topics[tid], question.id))
        cls.latest_question[tid] = cls(tid, question=question)

    def save(self):
        DB.save_question(self)

    @classmethod
    def get_all(cls, tid):
        questions = []
        for doc in DB.get_questions(tid):
            questions.append(cls.doc2question(doc))
        return questions

    @classmethod
    def doc2question(cls, doc):
        return cls(doc['topic'], doc['url'], doc['qid'], doc['asker'],
                   doc['time'], doc['title'])

    def __eq__(self, other):
        # title may change
        return self.url == other.url and self.qid == other.qid and \
               self.time == other.time and self.asker == other.asker

    def __str__(self):
        time_tuple = (self.time.hour, self.time.minute, self.time.second)
        return "{0}:{1}:{2} {3}".format(*time_tuple, self.title)


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


class User:
    def __init__(self):
        pass

    def save(self):
        pass
