"""
sort unsorted question followers according to time
"""

import pymongo

q_colls = ["19550517_q", "19551147_q", "19561087_q", "19553298_q"]

def sort_followers(db_name):
    # f = open('data/alltime.txt', 'w')
    db = pymongo.MongoClient('127.0.0.1:27017').get_database(db_name)
    for colname in q_colls:
        collection = db.get_collection(colname)
        for qdoc in collection.find():
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
            for follow in followers:
                if follow['time'] is None:  # 暂时不管那些有None的
                    break
            else:
                # f.write('%s,%s,%d\n' % (qdoc['topic'], qdoc['qid'], len(followers)))
                followers.sort(key=lambda x: x['time'])

            collection.update(
                {'qid': qdoc['qid']},
                {'$set': {'follower': followers}}
            )
    # f.close()

if __name__ == '__main__':
    # sort_followers('zhihu_data_0219')
    sort_followers('zhihu_data_0315')
