# coding: utf-8

"""
ORM-like class
"""

import ezcf

from config.dynamic_config import topics
from db import DB



class QuestionModel:

    latest_question = {
        tid: None for tid in topics  # for cache
    }

    def __init__(self, url=None, qid=None, asker=None, time=None, question=None):
        if question:
            self.url = question.url
            self.qid = question.id
            self.time = question.creation_time
            # self.asker = question.asker  TODO: add asker attr
            self.asker = "non-exist asker"
        else:
            self.url = url
            self.qid = qid
            self.time = time
            self.asker = asker
        self.answers = []

    @classmethod
    def is_latest(cls, tid, Question):
        if cls.latest_question[tid]:
            return cls.latest_question[tid].qid == Question.id
        else:
            doc = DB.find_latest_question(tid)
            if doc:
                cls.latest_question[tid] = cls(doc['url'], doc['qid'],
                                               doc['asker'], doc['time'])
                return doc['qid'] == Question.id
            else:
                # 第一次执行, 外部 set_latest 不会调用, 在这里初始化
                cls.set_latest(tid, Question)
                return True

    @classmethod
    def set_latest(cls, tid, Question):
        print("set latest question of tid: %s to %s" % (topics[tid], Question.id))
        cls.latest_question[tid] = cls(question=Question)

    def save(self, tid):
        DB.save_question(self, tid)



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
