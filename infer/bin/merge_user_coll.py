"""
【DEPRECATED】merge sg1 and zhihu_data_0315
"""
import pymongo


coll1 = pymongo.MongoClient('127.0.0.1', 27017).get_database('analysis').user
coll2 = pymongo.MongoClient('127.0.0.1', 27017).get_database('sg1').user

to_add = []
for udoc in coll2.find({}, {'uid': 1}):
    uid = udoc['uid']
    if coll1.find({'uid': uid}, {'_id': 1}).limit(1).count() == 0:
        print("add " + uid)
        to_add.append(uid)

for uid in to_add:
    udoc = coll2.find({'uid': uid}, {'_id': 0})
    coll1.insert(udoc)


