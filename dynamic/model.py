# coding: utf-8

"""
ORM-like class
"""

import logging

import ezcf

from config.dynamic_config import topics
from db import DB

logger = logging.getLogger(__name__)


class QuestionModel:

    latest_question = {
        tid: None for tid in topics  # for cache
    }

    def __init__(self, url=None, qid=None, asker=None, time=None, title=None,
                 question=None):
        if question:
            self.url = question.url
            self.qid = question.id
            self.time = question.creation_time
            self.title = question.title
            if question.author:
                self.asker = question.author.id
            else:
                self.asker = ''  # 匿名用户, TODO: zhihu-py3增加ANONYMOUS常量
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
            print("latest: ", cls.latest_question[tid])
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
        logger.debug("Set latest question of %s to %s" % (topics[tid], question.id))
        cls.latest_question[tid] = cls(question=question)

    def save(self, tid):
        DB.save_question(self, tid)

    @classmethod
    def get_all(cls, tid):
        questions = []
        for doc in DB.get_questions(tid):
            questions.append(cls.doc2question(doc))
        return questions

    @classmethod
    def doc2question(cls, doc):
        return cls(doc['url'], doc['qid'], doc['asker'], doc['time'], doc['title'])

    def __eq__(self, other):
        # title may change
        return self.url == other.url and self.qid == other.qid and \
               self.time == other.time and self.asker == other.asker

    def __str__(self):
        time_tuple = (self.time.hour, self.time.minute, self.time.second)
        return "{0}:{1}:{2} {3}".format(*time_tuple, self.title)



class AnswerModel:
    def __init__(self, aid, qid):
        self.aid = aid
        self.qid = qid
        self.url = "http://www.zhihu.com/question/%s/answer/%s" % (self.qid, self.aid)

    def save(self):
        # save to db
        pass


class User:
    def __init__(self):
        pass

    def save(self):
        pass
