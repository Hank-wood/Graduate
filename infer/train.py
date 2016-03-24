"""
训练 follow
"""
import sys
import time
import os
import pickle

import pymongo
from sklearn import svm, cross_validation

from feature import StaticAnswer
from user import UserManager
from iutils import a_col

db = pymongo.MongoClient('127.0.0.1', 27017).get_database('sg1')
sys.modules['feature'].__dict__['db'] = db
sys.modules['feature'].__dict__['user_manager'] = UserManager(db.user)

pickle_filename = 'data/feature.pkl'
if os.path.exists(pickle_filename):
    with open(pickle_filename, 'rb') as f:
        data = pickle.load(f)
else:
    data = {}


def gen_traindata_selected():
    """
    返回 alltime 中的 question 的 answer 的 follow 关系 train data
    :return: [features], [samples]
    """
    features = []
    samples = []
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
    return features, samples


def gen_traindata_from_all():
    """
    生成数据库中全部数据的 features, samples
    :return: [features] [samples]
    """
    features = []
    samples = []
    a_colls = ["19550517_a", "19551147_a", "19561087_a", "19553298_a"]
    for a_coll in a_colls:
        tid = a_coll[:-2]
        a_collection = db.get_collection(a_coll)
        for adoc in a_collection.find({}, {'aid': 1}):
            aid = adoc['aid']
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
    return features, samples


def train():
    clf = svm.SVC()
    features, samples = gen_traindata_selected()
    print(len(features))
    print(len(samples))
    with open(pickle_filename, 'wb') as f:
        pickle.dump(data, f)

    X_train, X_test, y_train, y_test = cross_validation.train_test_split(
        features, samples, test_size=0.4, random_state=0)
    clf.fit(X_train, y_train)
    print(clf.score(X_test, y_test))

    with open('data/model.pkl', 'wb') as f:
        pickle.dump(clf, f)


train()