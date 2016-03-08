"""
sort unsorted question followers according to time
"""

import pymongo


def sort_followers(db_name):
    f = open('data/alltime.txt', 'w')
    db = pymongo.MongoClient('127.0.0.1:27017').get_database(db_name)
    for colname in db.collection_names():
        if colname.endswith('q'):
            collection = db.get_collection(colname)
            for qdoc in collection.find():
                follows = qdoc['follower']
                if len(follows) <= 1:
                    continue
                for follow in follows:
                    if follow['time'] is None:  # 暂时不管那些有None的
                        break
                else:
                    f.write('%s,%s:%d\n' % (qdoc['topic'], qdoc['qid'], len(follows)))
                    follows.sort(key=lambda x: x['time'])
                    collection.update(
                        {'qid': qdoc['qid']},
                        {'$set': {'follower': follows}}
                    )
    f.close()

if __name__ == '__main__':
    # sort_followers('zhihu_data_0219')
    sort_followers('sg1')
