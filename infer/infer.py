import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import pymongo
from iutils import *
from icommon import db2
from component import DynamicQuestionWithAnswer, DynamicAnswer


def infer_one_question(tid, qid, aid, db_name):
    sys.modules['component'].__dict__['db'] = \
        pymongo.MongoClient('127.0.0.1', 27017).get_database(db_name)
    info_storage = DynamicQuestionWithAnswer(tid, qid)
    db = pymongo.MongoClient('127.0.0.1:27017').get_database(db_name)
    collection = db.get_collection(a_col(tid))

    answers = []
    for answer_doc in collection.find({'qid': qid}, {'aid': 1}):
        answers.append(DynamicAnswer(tid, answer_doc['aid'], info_storage))

    for answer in answers:
        if answer.aid == aid:
            answer.infer(save_to_db=False)


def infer_all(db_name):
    sys.modules['component'].__dict__['db'] = \
        pymongo.MongoClient('127.0.0.1', 27017, connect=False).get_database(db_name)
    db = pymongo.MongoClient('127.0.0.1:27017').get_database(db_name)
    executor = ProcessPoolExecutor(max_workers=5)

    futures = []
    for collection_name in db.collection_names():
        if not is_q_col(collection_name):
            continue
        tid = collection_name[:-2]
        q_collection = db[collection_name]
        a_collection = q_to_a(db[collection_name])
        for q_doc in q_collection.find({}, {'qid':1, 'topic':1}):
            qid = q_doc['qid']
            aids = [a_doc['aid'] for a_doc in
                    a_collection.find({'qid': qid}, {'aid': 1})]
            futures.append(executor.submit(infer_question_task, tid, qid, aids))

    inferred_answer_count = 0
    for f in as_completed(futures):
        inferred_answer_count += f.result()

    executor.shutdown()


def infer_many(db_name, filename):
    """
    推断一些问题的回答, 读取文件, 每一行格式为
    topic,qid,...(后面是什么无所谓)
    """
    sys.modules['component'].__dict__['db'] = \
        pymongo.MongoClient('127.0.0.1', 27017, connect=False).get_database(db_name)
    db = pymongo.MongoClient('127.0.0.1:27017').get_database(db_name)
    executor = ProcessPoolExecutor(max_workers=5)

    count = 0
    futures = []
    with open(filename) as f:
        for line in f:
            tid, qid, _ = line.split(',', maxsplit=2)
            a_collection = db[a_col(tid)]
            aids = [a_doc['aid'] for a_doc in
                    a_collection.find({'qid': qid}, {'aid': 1})]
            futures.append(executor.submit(infer_question_task, tid, qid, aids))
            count += len(aids)

    print(count)
    executor.shutdown()


def infer_question_task(tid, qid, aids):
    info_storage = DynamicQuestionWithAnswer(tid, qid)
    for aid in aids:
        # print("infer " + aid)
        DynamicAnswer(tid, aid, info_storage).infer(save_to_db=True)

    return len(aids)


if __name__ == '__main__':
    # infer_one_question(tid='19551147', qid='40554112', aid='87120100',db_name='zhihu_data_0219')
    # infer_one_question(tid='19551147', qid="40611516", aid="87420652",db_name='sg1')
    # infer_one_question(tid='19553298', qid="40617404", aid="87423946",db_name='sg1')
    infer_many(db_name='sg1', filename='data/alltime.txt')
