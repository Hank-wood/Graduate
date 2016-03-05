"""
用来确保 question follower 按时间排序
"""

import pymongo
from datetime import datetime

q_colls = ["19550517_q", "19551147_q", "19561087_q", "19553298_q"]
db = pymongo.MongoClient('127.0.0.1', 27017).zhihu_data

for q_coll in q_colls:
    coll = db.get_collection(q_coll)
    for qdoc in coll.find():
        followers = qdoc['follower']
        last_datetime = datetime(1970,1,1)
        for f in followers:
            if f['time'] is None:
                continue
            curr_datetime = f['time']
            if curr_datetime >= last_datetime:
                last_datetime = curr_datetime
            else:
                print(q_coll + "'s question" + qdoc['qid'])
                print(qdoc['follower'])

        print(qdoc['qid'] + " is OK")
