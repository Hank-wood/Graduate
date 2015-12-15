# coding: utf-8

"""
ORM-like class
"""

import ezcf

from config.dynamic_config import topics
import db


class Question:

    latest_question = {
        tid: None for tid in topics  # for cache
    }

    def __init__(self, qid):
        self.qid = qid

    @classmethod
    def get_latest_question(self, tid):
        if self.latest_question[tid] is None:
            self.latest_question[tid] = db.find_latest_question(tid)

        return self.latest_question[tid]

    def save(self):
        pass



class Answer:
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
