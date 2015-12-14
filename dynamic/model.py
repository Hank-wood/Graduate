# coding: utf-8

"""
ORM-like class
"""

import ezcf

from config.dynamic_config import topics
import db


class Question:

    latest_question = {
        topic_id: None for topic_id in topics  # for cache
    }

    def __init__(self, qid):
        self.qid = qid

    @classmethod
    def get_latest_question(self, topic_id):
        if self.latest_question[topic_id] is None:
            self.latest_question[topic_id] = db.find_latest_question(topic_id)

        return self.latest_question[topic_id]

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
