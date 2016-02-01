# coding: utf-8

"""
数据库接口
"""

from pymongo import MongoClient

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
    def save_question(cls, tid, url, qid, time, asker, title):
        cls.db[q_col(tid)].insert({
            'topic': str(tid),
            'url': url,
            'qid': str(qid),
            'time': time,
            'asker': asker,
            'title': title,
            'follower': []
        })

    @classmethod
    def add_question_follower(cls, tid, qid, new_followers):
        cls.db[q_col(tid)].update({'qid': str(qid)}, {
            '$push': {
                'follower': {
                    '$each': list(new_followers)
                }
            }
        })

    @classmethod
    def get_question_follower(cls, tid, qid, limit=None):
        if limit is None:
            return cls.db[q_col(tid)].\
                find_one({'qid': str(qid)}, {'follower': 1, '_id':0})['follower']
        else:
            return cls.db[q_col(tid)]. \
                find_one({'qid': str(qid)},
                         {'follower': {'$slice': limit}, '_id':0})['follower']

    @classmethod
    def get_question_follower_num(cls, tid, qid):
        cursor = cls.db[q_col(tid)].aggregate([
            {'$match': {'qid': qid}},
            {
                '$project': {
                    'follower_count': {'$size': "$follower"}
                }
            }
        ])
        return list(cursor)[0]['follower_count']

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
        return cls.db[q_col(tid)].find_one({'qid': str(qid)})  # None or dict

    @classmethod
    def get_all_questions(cls):
        result = []
        for collection_name in cls.db.collection_names():
            import utils
            if is_q_col(collection_name):
                result.extend(list(cls.db[collection_name].find({})))

        return result

    @classmethod
    def get_question_attrs(cls, tid, qid, *args):
        fields = {arg: 1 for arg in args}
        return cls.db[q_col(tid)].find_one({'qid': str(qid)}, fields)

    @classmethod
    def remove_question(cls, tid, qid):
        cls.db[q_col(tid)].remove({'qid': str(qid)})

    @classmethod
    def bulk_save(cls):
        pass

    @classmethod
    def add_upvoters(cls, tid, aid, new_upvoters):
        cls.db[a_col(tid)].update({'aid': str(aid)}, {
            '$push': {
                'upvoters': {
                    '$each': list(new_upvoters)
                }
            }
        })

    @classmethod
    def add_commenters(cls, tid, aid, new_commenters):
        # pymongo不识别deque,只能转为list
        cls.db[a_col(tid)].update({'aid': str(aid)}, {
            '$push': {
                'commenters': {
                    '$each': list(new_commenters)
                }
            }
        })

    @classmethod
    def add_collectors(cls, tid, aid, new_collectors):
        cls.db[a_col(tid)].update({'aid': str(aid)}, {
           '$push': {
               'collectors': {
                   '$each': list(new_collectors)
               }
           }
       })

    @classmethod
    def find_one_answer(cls, tid, aid):
        return cls.db[a_col(tid)].find_one({'aid': str(aid)})

    @classmethod
    def remove_answer(cls, tid, aid):
        cls.db[a_col(tid)].remove({'aid': str(aid)})

    @classmethod
    def get_question_answerer(cls, tid, qid):
        return cls.db[a_col(tid)].find({'qid': qid}, {'answerer': 1, '_id': 0})

    @classmethod
    def get_question_answer_attrs(cls, tid, qid, *args):
        fields = {arg: 1 for arg in args}
        return cls.db[a_col(tid)].find({'qid': qid}, fields)

    @classmethod
    def drop_all_collections(cls):
        for collection_name in cls.db.collection_names():
            if 'system' not in collection_name:
                cls.db[collection_name].drop()
