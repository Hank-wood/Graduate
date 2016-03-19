"""
移除某个时间点之后提出的问题, 以及它们的答案. 在程序出问题时使用
"""

from datetime import datetime

import pymongo

t = datetime(2016,3,11,18,0,0)

db = pymongo.MongoClient('127.0.0.1', 27017).zhihu_data
q_colls = ["19550517_q", "19551147_q", "19561087_q", "19553298_q"]

for q_coll in q_colls:
    coll = db.get_collection(q_coll)
    acoll = db.get_collection(q_coll[:-1] + 'a')
    for qdoc in coll.find():
        if qdoc['time'] < t:
            result = coll.delete_one({'qid': qdoc['qid']})
            assert result.deleted_count == 1
            print("question %s removed" % qdoc['qid'])
            result = acoll.delete_many({'qid': qdoc['qid']})
            print("%d answers removed" % result.deleted_count)
