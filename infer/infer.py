import sys
import multiprocessing

import pymongo
from iutils import *
from component import InfoStorage, Answer


def infer_one_question(tid, qid, db_name):
    sys.modules['component'].__dict__['db'] = \
        pymongo.MongoClient('127.0.0.1', 27017).get_database(db_name)
    info_storage = InfoStorage(tid, qid)
    db = pymongo.MongoClient('127.0.0.1:27017').get_database(db_name)
    collection = db.get_collection(a_col(tid))

    answers = []
    for answer_doc in collection.find({'qid': qid}, {'aid': 1}):
        answers.append(Answer(tid, answer_doc['aid'], info_storage))

    for answer in answers:
        if answer.aid == '87120100':
            answer.infer(save_to_db=False)


def infer_all(db_name):
    sys.modules['component'].__dict__['db'] = \
        pymongo.MongoClient('127.0.0.1', 27017).get_database(db_name)
    db = pymongo.MongoClient('127.0.0.1:27017').get_database(db_name)
    for collection_name in db.collection_names():
        if not is_q_col(collection_name):
            continue
        q_collection = db[collection_name]
        a_collection = q_to_a(db[collection_name])
        for q_doc in q_collection.find({}, {'qid':1, 'topic':1}):
            info_storage = InfoStorage(q_doc['topic'], q_doc['qid'])
            for a_doc in a_collection.find({'qid': q_doc['qid']}, {'aid': 1}):
                Answer(q_doc['topic'], a_doc['aid'], info_storage).infer(True)


if __name__ == '__main__':
    infer_one_question(tid='19551147', qid='40554112', db_name='zhihu_data_0219')
