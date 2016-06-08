"""
检测 user follow/followee 的时间有无 None
"""

import pymongo
from pprint import pprint

db = pymongo.MongoClient('127.0.0.1', 27017).test
print(db.user.find().count())
count = 0

for user in db.user.find({}):
    for f in user.get('followee', []):
        if f['time'] is None:
            pprint(user)
            count += 1
            break
    else:
        for f in user.get('follower', []):
            if f['time'] is None:
                pprint(user)
                count += 1
                break

print(count)