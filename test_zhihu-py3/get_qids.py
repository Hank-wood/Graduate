import pymongo

db = pymongo.MongoClient('127.0.0.1', 27017).zhihu_data

qset = set()

for collection_name in db.collection_names():
    if 'a' in collection_name:
        for answer in db[collection_name].find():
            qset.add(answer['qid'])

print(qset)
