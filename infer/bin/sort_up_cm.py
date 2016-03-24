"""
sort upvoters and commenters
"""

import pymongo
from datetime import datetime

database = 'sg1'

a_colls = ["19550517_a", "19551147_a", "19561087_a", "19553298_a"]
db = pymongo.MongoClient('127.0.0.1', 27017).get_database(database)

for colname in a_colls:
    collection = db.get_collection(colname)
    for adoc in collection.find():
        # gen sorted upvoters
        upvoters = adoc['upvoters']
        if len(upvoters) > 1:
            last_upvote_time = datetime(1970,1,1)
            sorted_upvoters = []
            upvote_ids = set()
            for upvote in upvoters:
                if upvote['uid'] not in upvote_ids and upvote['time'] is None:
                    sorted_upvoters.append(upvote)
                    upvote_ids.add(upvote['uid'])
                elif upvote['uid'] not in upvote_ids and upvote['time'] > last_upvote_time:
                    sorted_upvoters.append(upvote)
                    last_upvote_time = upvote['time']
                    upvote_ids.add(upvote['uid'])
        else:
            sorted_upvoters = upvoters

        # gen sorted commenters
        commenters = adoc['commenters']
        if len(commenters) > 1:
            commenters.sort(key=lambda x: x['time'])

        # write back
        collection.update(
            {'aid': adoc['aid']},
            {'$set': {'upvoters': sorted_upvoters, 'commenters': commenters}}
        )
