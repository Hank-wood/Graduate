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
            'topic': str(question.tid),
            'url': question.url,
            'qid': str(question.qid),
            'time': question.time,
            'asker': question.asker,
            'title': question.title,
            'answers': question.answers
        })

    @classmethod
    def save_answer(cls, tid, aid, url, qid, time, answerer, upvoters=None,
                    commenters=None, collectors=None):
        upvoters = [] if upvoters is None else upvoters
        commenters = [] if commenters is None else commenters
        collectors = [] if collectors is None else collectors

        cls.db[a_col(tid)].insert({
            'topic': str(tid),
            'aid': str(aid),
            'url': url,
            'qid': str(qid),
            'time': time,
            'answerer': answerer,
            'upvoters': upvoters,
            'commenters': commenters,
            'collectors': collectors
        })

    @classmethod
    def get_question(cls, tid, qid):
        return cls.db[q_col(tid)].find_one({'qid': qid})  # None or dict

    @classmethod
    def remove_question(cls, tid, qid):
        cls.db[q_col(tid)].remove({'qid': qid})

    @classmethod
    def bulk_save(cls):
        pass

    @classmethod
    def add_upvoters(cls, tid, aid, new_upvoters):
        cls.db[a_col(tid)].update({'aid': aid}, {
            '$push': {
                'upvoters': {
                    '$each': list(new_upvoters)
                }
            }
        })

    @classmethod
    def add_commenters(cls, tid, aid, new_commenters):
        # pymongo不识别deque,只能转为list
        cls.db[a_col(tid)].update({'aid': aid}, {
            '$push': {
                'commenters': {
                    '$each': list(new_commenters)
                }
            }
        })

    @classmethod
    def add_collectors(cls, tid, aid, new_collectors):
        cls.db[a_col(tid)].update({'aid': aid}, {
           '$push': {
               'collectors': {
                   '$each': list(new_collectors)
               }
           }
       })

    @classmethod
    def find_one_answer(cls, tid, aid):
        return cls.db[a_col(tid)].find_one({'aid': aid})

    @classmethod
    def drop_all_collections(cls):
        for collection in cls.db.collection_names():
            cls.db[collection].drop()
