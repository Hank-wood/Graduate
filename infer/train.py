"""
训练 follow
"""
import sys
import time
import os
import pickle

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

pickle_filename = 'data/feature.pkl'
if os.path.exists(pickle_filename):
    data = pickle.load(open(pickle_filename, 'rb'))
else:
    data = {}

with open('data/alltime.txt') as f:
    for line in f:
        tid, qid, _ = line.split(',', maxsplit=2)
        a_collection = db[a_col(tid)]
        aids = [a_doc['aid'] for a_doc in
                a_collection.find({'qid': qid}, {'aid': 1})]
        for aid in aids:
            answer = StaticAnswer(tid, aid)
            if aid not in data:
                answer.load_from_dynamic()
                answer.build_cand_edges()
                target = answer.gen_target()
                f = answer.gen_features()
                data[aid] = {
                    'edge': answer.cand_edges,
                    'target': target,
                    'feature': f
                }
                samples.extend(target)
                features.extend(f)
            else:
                samples.extend(data[aid]['target'])
                features.extend(data[aid]['feature'])

pickle.dump(data, open(pickle_filename, 'wb'))

print(len(features))
print(len(samples))
print(time.time() - start)
print(clf.fit(features, samples))
print(time.time() - start)
