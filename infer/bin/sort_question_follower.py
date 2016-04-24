"""
sort unsorted question followers according to time
"""

import pymongo
from pprint import pprint as print

q_colls = ["19550517_q", "19551147_q", "19561087_q", "19553298_q"]

qids = (
    '40659646'
)

def sort_followers(db_name):
    # f = open('data/alltime.txt', 'w')
    db = pymongo.MongoClient('127.0.0.1:27017').get_database(db_name)
    for colname in q_colls:
        collection = db.get_collection(colname)
        for qdoc in collection.find():
            if qdoc['qid'] not in qids:
                continue
            print(qdoc['qid'])
            followers = qdoc['follower']
            follower_ids = set()
            if len(followers) <= 1:
                continue
            # remove duplicates
            distinct_followers = []
            for follow in followers:
                if follow['uid'] not in follower_ids:
                    follower_ids.add(follow['uid'])
                    distinct_followers.append(follow)
            followers = distinct_followers
            for index, follow in enumerate(followers):
                print(index)
                if follow['time'] is None:  # 暂时不管那些有None的
                    low = min(followers[index-1]['time'], followers[index+1]['time'])
                    high = max(followers[index-1]['time'], followers[index+1]['time'])
                    follow['time'] = low + (high - low) / 2

            collection.update(
                {'qid': qdoc['qid']},
                {'$set': {'follower': followers}}
            )
    # f.close()

if __name__ == '__main__':
    # sort_followers('zhihu_data_0219')
    sort_followers('sg1')
