# coding: utf-8

"""
数据库接口
"""

from pymongo import MongoClient
import ezcf

from config.dynamic_config import topics
from utils import *


class DB:
    db = MongoClient('127.0.0.1', 27017).zhihu_data

    @classmethod
    def find_user(cls):
        pass

    @classmethod
    def get_questions(cls, tid):
        return cls.db[q_col(tid)].find()

    @classmethod
    def find_latest_question(cls, tid):
        # TODO: so ask: 如何建索引?
        cursor = cls.db[q_col(tid)].find().sort('time', -1)
        if cursor.count() > 0:
            return cursor[0]
        else:
            return None

    @classmethod
    def save_question(cls, question):
        cls.db[q_col(question.tid)].insert({
            'topic': question.tid,
            'url': question.url,
            'qid': question.qid,
            'time': question.time,
            'asker': question.asker,
            'title': question.title,
            'answers': question.answers
        })

    @classmethod
    def save_answer(cls, answer):
        cls.db[a_col(answer.tid)].insert({
            'url': answer.url,
            'qid': answer.qid,
            'aid': answer.aid,
            'topic': answer.tid,
            'time': answer.time,
            'answerer': answer.answerer,
            'upvoters': answer.upvoters,
            'commenters': answer.commenters,
            'collectors': answer.collectors
        })

    @classmethod
    def get_question(cls, tid, qid):
        return cls.db[q_col(tid)].find_one({'qid': qid})  # None or dict

    @classmethod
    def bulk_save(cls):
        pass

    @classmethod
    def drop_all_collections(cls):
        for collection in cls.db.collection_names():
            cls.db[collection].drop()
