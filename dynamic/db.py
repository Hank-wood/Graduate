# coding: utf-8

"""
数据库接口
"""

from pymongo import MongoClient

from utils import *


class DB:
    """
    尽可能不对 doc 作处理，直接返回 query 的结果。由 manager 作进一步处理。
    """
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
            'follower': [],
            'active': True
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
            limit *= -1
            return cls.db[q_col(tid)]. \
                find_one({'qid': str(qid)},
                         {'follower': {'$slice': limit}, '_id':0})['follower']

    @classmethod
    def get_question_follower_num(cls, tid, qid):
        cursor = cls.db[q_col(tid)].aggregate([
            {'$match': {'qid': str(qid)}},
            {
                '$project': {
                    'follower_count': {'$size': "$follower"}
                }
            }
        ])
        return list(cursor)[0]['follower_count']

    @classmethod
    def set_question_inactive(cls, tid, qid):
        cls.db[q_col(tid)].update_one(
            {'qid': str(qid)},
            {
                '$set': {
                    'active': False
                }
            }
        )

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
    def get_all_questions(cls, *args):
        result = []
        if args:
            fields = {arg: 1 for arg in args}
        else:
            fields = {'_id': 0}   # include all fields
        for collection_name in cls.db.collection_names():
            if is_q_col(collection_name):
                result.extend(
                    list(cls.db[collection_name].find({}, fields))
                )

        return result

    @classmethod
    def get_question_attrs(cls, tid, qid, *args):
        fields = {arg: 1 for arg in args}
        return cls.db[q_col(tid)].find_one({'qid': str(qid)}, fields)

    @classmethod
    def remove_question(cls, tid, qid):
        cls.db[q_col(tid)].remove({'qid': str(qid)})

    @classmethod
    def answer_exists(cls, tid, aid):
        return cls.db[a_col(tid)].find({'aid': str(aid)}, {'_id': 1}) \
                  .limit(1).count() > 0

    @classmethod
    def get_one_answer(cls, tid, aid):
        return cls.db[a_col(tid)].find_one({'aid': str(aid)})

    @classmethod
    def get_answer_affected_user_with_limit(cls, tid, aid, limit=5):
        limit *= -1
        return cls._get_answer_affected_user(
            tid, aid, ['commenters', 'upvoters', 'collectors'], limit=limit)

    @classmethod
    def get_upvoters(cls, tid, aid, limit=None):
        return cls._get_answer_affected_user(tid, aid, ['upvoters'], limit)

    @classmethod
    def get_commenters(cls, tid, aid, limit=None):
        return cls._get_answer_affected_user(tid, aid, ['commenters'], limit)

    @classmethod
    def get_collectors(cls, tid, aid, limit=None):
        return cls._get_answer_affected_user(tid, aid, ['collectors'], limit)

    @classmethod
    def _get_answer_affected_user(cls, tid, aid, fields, limit=None):
        if limit is None:
            fields = {field: 1 for field in fields}
            return cls.db[a_col(tid)].find_one({'aid': str(aid)}, fields)
        else:
            limit *= -1
            fields = {field: {'$slice': limit} for field in fields}
            return cls.db[a_col(tid)].find_one({'aid': str(aid)}, fields)

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
    def remove_answer(cls, tid, aid):
        cls.db[a_col(tid)].remove({'aid': str(aid)})

    @classmethod
    def get_question_answerer(cls, tid, qid):
        return cls.db[a_col(tid)].find(
                {'qid': str(qid)},
                {'answerer': 1, '_id': 0}
        )

    @classmethod
    def get_question_answer_attrs(cls, tid, qid, *args):
        fields = {arg: 1 for arg in args}
        return cls.db[a_col(tid)].find({'qid': str(qid)}, fields)

    @classmethod
    def drop_all_collections(cls):
        for collection_name in cls.db.collection_names():
            if 'system' not in collection_name:
                cls.db[collection_name].drop()

    @classmethod
    def drop_qa_collections(cls):
        for collection_name in cls.db.collection_names():
            if 'system' not in collection_name and collection_name != 'user':
                cls.db[collection_name].drop()

    @classmethod
    def get_answer_affecter_num(cls, tid, aid):
        cursor = cls.db[a_col(tid)].aggregate([
            {'$match': {'aid': str(aid)}},
            {
                '$project': {
                    'up_count': {'$size': "$upvoters"},
                    'com_count': {'$size': "$commenters"},
                    'col_count': {'$size': "$collectors"},
                }
            }
        ])
        return list(cursor)[0]
