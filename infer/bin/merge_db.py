"""
【DEPRECATED】merge sg1 and zhihu_data_0315
"""
import pymongo


# 检测是否有重复问题
q_colls = ["19550517_q", "19551147_q", "19561087_q", "19553298_q"]
db1 = pymongo.MongoClient('127.0.0.1', 27017).get_database('sg1')
db2 = pymongo.MongoClient('127.0.0.1', 27017).get_database('zhihu_data_0315')

count = 0
for qcol_name in q_colls:
    col1 = db1.get_collection(qcol_name)
    col2 = db2.get_collection(qcol_name)
    for qdoc in col1.find():
        qid = qdoc['qid']
        k = col2.find({'qid': qid}, {'_id': 1}).count()
        if k != 0:
            assert qdoc['time'] == col2.find_one({'qid': qid}, {'time':1})['time']
            count += 1

print(count)  # 0 no question appear twice


qdoc = db2.get_collection('19550517_q').find_one({'qid': '41864611'})
with open('followers', 'w') as f:
    for follower in qdoc['follower']:
        f.write(str(follower) + '\n')