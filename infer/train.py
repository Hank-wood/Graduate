"""
训练 follow
"""
import sys
import time
import os
import pickle

import pymongo
from sklearn import svm, cross_validation
from sklearn.grid_search import GridSearchCV

from feature import StaticAnswer, FeatureContainer
from user import UserManager
from iutils import a_col

db = pymongo.MongoClient('127.0.0.1', 27017).get_database('zhihu_data_0315')
sys.modules['feature'].__dict__['db'] = db
sys.modules['feature'].__dict__['user_manager'] = UserManager(db.user)

pickle_filename = 'data/feature_0315.pkl'


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
                        'edge': answer.cand_follow_edges,
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
    生成数据库中全部数据的 features, samples. 用于从无到有生成边,特征,所以只需调用一次
    """
    fc = FeatureContainer()
    a_colls = ["19550517_a", "19551147_a", "19561087_a", "19553298_a"]
    try:
        for a_coll in a_colls:
            count = 0
            print(a_coll)
            tid = a_coll[:-2]
            a_collection = db.get_collection(a_coll)
            # 保证答案的遍历顺序不变
            for adoc in a_collection.find({}, {'aid': 1}).sort([('aid', 1)]):
                count += 1
                aid = adoc['aid']
                answer = StaticAnswer(tid, aid)
                answer.load_from_dynamic()
                answer.build_cand_edges()
                fc.append(answer.gen_features(), answer.gen_target())
    except:
        print(count)
        raise
    fc.dump(pickle_filename)
    print(len(fc.features))


def feature_selection():
    import numpy as np
    from sklearn.cross_validation import cross_val_score
    fc = FeatureContainer()
    fc.load(pickle_filename)
    clf = svm.SVC()
    print("number of 0: %d" % fc.target.count(0))
    print("number of 1: %d" % fc.target.count(1))

    # 值越小越好
    print("use all features")
    print(np.sqrt(-cross_val_score(clf, fc.features, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    # 每次排除一个特征
    print("\nexlucde h_rank")
    F = fc.get_features(('is_answer', 'is_upvote', 'is_comment',
                         'is_collect', 'r_order'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    print("\nexlucde is_answer")
    F = fc.get_features(('h_rank','is_upvote','is_comment',
                        'is_collect', 'r_order'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    print("\nexlucde is_upvote")
    F = fc.get_features(('h_rank', 'is_answer', 'is_comment',
                         'is_collect', 'r_order'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    print("\nexlucde is_comment")
    F = fc.get_features(('h_rank', 'is_answer', 'is_upvote',
                         'is_collect', 'r_order'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    print("\nexlucde is_collect")
    F = fc.get_features(('h_rank', 'is_answer', 'is_upvote','is_comment',
                         'r_order'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    print("\nexlucde r_order")
    F = fc.get_features(('h_rank', 'is_answer', 'is_upvote','is_comment',
                         'is_collect'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    # exclude is_answer and another feature
    print("\nexlucde is_answer hrank")
    F = fc.get_features(('is_upvote', 'is_comment', 'is_collect', 'r_order'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    print("\nexlucde is_answer is_upvote ")
    F = fc.get_features(('h_rank', 'is_comment', 'is_collect', 'r_order'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    print("\nexlucde is_answer is_comment")
    F = fc.get_features(('h_rank', 'is_upvote', 'is_collect', 'r_order'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    print("\nexlucde is_answer is_collect")
    F = fc.get_features(('h_rank', 'is_upvote', 'is_comment', 'r_order'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())

    print("\nexlucde is_answer r_order")
    F = fc.get_features(('h_rank', 'is_upvote', 'is_comment', 'is_collect'))
    print(np.sqrt(-cross_val_score(clf, F, fc.target, cv=10,
                                   scoring='mean_squared_error')).mean())


def param_tuning():
    # Set the parameters by cross-validation
    tuned_parameters = [{'kernel': ['rbf'], 'gamma': [1e-3, 1e-4],
                         'C': [1, 10, 100, 1000]},
                        {'kernel': ['linear'], 'C': [1, 10, 100, 1000]}]

    scores = ['accuracy', 'recall']

    for score in scores:
        print("# Tuning hyper-parameters for %s" % score)
        print()

        clf = GridSearchCV(svm.SVC(C=1), tuned_parameters, cv=10,
                           scoring=score)
        fc = FeatureContainer()
        fc.load(pickle_filename)
        F = fc.get_features(('h_rank','is_upvote','is_comment',
                             'is_collect', 'r_order'))
        print(len(F))
        print(len(fc.target))
        clf.fit(F, fc.target)

        print("Best parameters set found on development set:")
        print()
        print(clf.best_params_)
        print()
        print("Grid scores on development set:")
        print()
        for params, mean_score, scores in clf.grid_scores_:
            print("%0.3f (+/-%0.03f) for %r"
                  % (mean_score, scores.std() * 2, params))
        print()


def train():
    clf = svm.SVC(**{'C': 1, 'kernel': 'rbf', 'gamma': 0.0001},
                  probability=True)
    print(clf.C, clf.kernel, clf.gamma)
    fc = FeatureContainer()
    fc.load(pickle_filename)
    F = fc.get_features(('h_rank', 'is_upvote', 'is_comment',
                         'is_collect', 'r_order'))
    clf.fit(F, fc.target)

    with open('data/model_0315.pkl', 'wb') as f:
        pickle.dump(clf, f)


if __name__ == '__main__':
    # gen_traindata_from_all()
    # feature_selection()
    # param_tuning()
    train()
