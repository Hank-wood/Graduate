"""
训练 follow
"""
import sys
import time

import pymongo
from sklearn import svm

from feature import StaticAnswer
from user import UserManager
from iutils import a_col

db = pymongo.MongoClient('127.0.0.1', 27017).get_database('sg1')
sys.modules['feature'].__dict__['db'] = db
sys.modules['feature'].__dict__['user_manager'] = UserManager(db.user)
clf = svm.SVC()

features = []
samples = []
start = time.time()
with open('data/alltime.txt') as f:
    for line in f:
        tid, qid, _ = line.split(',', maxsplit=2)
        a_collection = db[a_col(tid)]
        aids = [a_doc['aid'] for a_doc in
                a_collection.find({'qid': qid}, {'aid': 1})]
        for aid in aids:
            answer = StaticAnswer(tid, aid)
            answer.load_from_dynamic()
            answer.build_cand_edges()
            samples.extend(answer.gen_target())
            features.extend(answer.gen_features())

print(len(features))
print(len(samples))
print(time.time() - start)
clf.fit(features, samples)
print(time.time() - start)
