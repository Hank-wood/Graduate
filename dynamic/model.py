# coding: utf-8

"""
ORM-like class
"""

import ezcf

from config.dynamic_config import topics
from db import DB


db = DB()


class QuestionModel:

    latest_question = {
        tid: None for tid in topics  # for cache
    }

    def __init__(self, Question=None, qid=None, time=None):
        if Question:
            self.qid = Question.id
            self.time = Question.creation_time
        else:
            self.qid = qid
            self.time = time
        self.answers = []

    @classmethod
    def is_latest(cls, tid, Question):
        if cls.latest_question[tid]:
            print(topics[tid], str(cls.latest_question[tid].qid), str(Question.id))
            return cls.latest_question[tid].qid == Question.id
        else:
            doc = db.find_latest_question(tid)
            if doc:
                cls.latest_question[tid] = cls(qid=doc['qid'], time=doc['time'])
                return doc['qid'] == Question.id
            else:
                # 第一次执行, 外部 set_latest 不会调用, 在这里初始化
                cls.set_latest(tid, Question)
                return True

    @classmethod
    def set_latest(cls, tid, Question):
        print("set latest question of tid: %s to %s" % (tid, Question.id))
        cls.latest_question[tid] = cls(Question)

    def save(self):
        pass



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
