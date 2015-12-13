# coding: utf-8

"""
ORM-like class
"""

import db


class Answer:
    def __init__(self, aid, qid):
        self.aid = aid
        self.qid = qid
        self.url = "http://www.zhihu.com/question/%s/answer/%s" % (self.qid, self.aid)

    @classmethod
    def get_latest_question(self, topic):
        return "get data from db"

    def save(self):
        # save to db
        pass


class User:
    def __init__(self):
        pass

    def save(self):
        pass
