"""
删除问题不在数据库中的回答
"""
import pymongo


db = pymongo.MongoClient('127.0.0.1', 27017).get_database('zhihu_data_0315')
a_colls = ["19550517_a", "19551147_a", "19561087_a", "19553298_a"]
for a_coll in a_colls:
    q_coll = a_coll[:-1] + 'q'
    a_collection = db.get_collection(a_coll)
    q_collection = db.get_collection(q_coll)
    for adoc in a_collection.find():
        qid = adoc['qid']
        if q_collection.find({'qid': qid}, {'_id': 1}).count() == 0:
            print("%s %s %s" % (a_coll, qid, adoc['url']))
            result = a_collection.delete_many({'qid': qid})
            print(result.deleted_count)

