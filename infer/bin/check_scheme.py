import pymongo
from datetime import datetime

database = 'sg1'

a_colls = ["19550517_a", "19551147_a", "19561087_a", "19553298_a"]
db = pymongo.MongoClient('127.0.0.1', 27017).get_database(database)
start_search_time = datetime(1970,1,1)  # change this before run

# check upvoters sorted
for a_coll in a_colls:
    coll = db.get_collection(a_coll)
    for adoc in coll.find({'time': {'$gt': start_search_time}}):
        followers = adoc['upvoters']
        last_datetime = datetime(1970,1,1)
        sort = True
        for f in followers:
            if f['time'] is None:
                continue
            curr_datetime = f['time']
            if curr_datetime >= last_datetime:
                last_datetime = curr_datetime
            else:
                sort = False
                break

        if not sort:
            print(f)
            print("upvoters unsorted:", end=' ')
            print("tid:%s aid:%s" % (a_coll, adoc['aid']))
            with open('../data/upvoters_' + adoc['aid'], 'w') as f:
                for upvoter in adoc['upvoters']:
                    f.write("%s %s\n" % (upvoter['uid'], str(upvoter['time'])))

# check commenters sorted
for a_coll in a_colls:
    coll = db.get_collection(a_coll)
    for adoc in coll.find({'time': {'$gt': start_search_time}}):
        followers = adoc['commenters']
        last_datetime = datetime(1970,1,1)
        sort = True
        for f in followers:
            if f['time'] is None:
                continue
            curr_datetime = f['time']
            if curr_datetime >= last_datetime:
                last_datetime = curr_datetime
            else:
                sort = False
                break

        if not sort:
            print("commenters unsorted:", end=' ')
            print("tid:%s aid:%s" % (a_coll, adoc['aid']))

# check commenters sorted
for a_coll in a_colls:
    coll = db.get_collection(a_coll)
    for adoc in coll.find({'time': {'$gt': start_search_time}}):
        followers = adoc['collectors']
        last_datetime = datetime(1970,1,1)
        sort = True
        for f in followers:
            if f['time'] is None:
                continue
            curr_datetime = f['time']
            if curr_datetime >= last_datetime:
                last_datetime = curr_datetime
            else:
                sort = False
                break

        if not sort:
            print("collectors unsorted:", end=' ')
            print("tid:%s aid:%s" % (a_coll, adoc['aid']))


q_colls = ["19550517_q", "19551147_q", "19561087_q", "19553298_q"]

for q_coll in q_colls:
    coll = db.get_collection(q_coll)
    for qdoc in coll.find({'time': {'$gt': start_search_time}}):
        followers = qdoc['follower']
        last_datetime = datetime(1970,1,1)
        sort = True
        for f in followers:
            if f['time'] is None:
                continue
            curr_datetime = f['time']
            if curr_datetime >= last_datetime:
                last_datetime = curr_datetime
            else:
                sort = False
                last_datetime = curr_datetime
        if not sort:
            print("question followers unsorted:", end=' ')
            print("tid:%s aid:%s" % (q_coll, qdoc['qid']))

# check 问题唯一, should print []
for q_coll in q_colls:
    result = db[q_coll].aggregate([
        {
            "$group": {
                "_id": {"qid": "$qid"},   # replace `name` here twice
                "uniqueIds": {"$addToSet": "$_id"},
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {
                "count": {"$gte": 2}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ])
    print(list(result))

# check 回答唯一, should print []
for a_coll in a_colls:
    result = db[a_coll].aggregate([
        {
            "$group": {
                "_id": {"aid": "$aid"},   # replace `name` here twice
                "uniqueIds": {"$addToSet": "$_id"},
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {
                "count": {"$gte": 2}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ])
    print(list(result))
