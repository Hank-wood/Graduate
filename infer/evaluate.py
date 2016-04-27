import sys
import pickle
import pymongo
import os.path
from sklearn import metrics

from iutils import *
from icommon import db2
from feature import StaticQuestionWithAnswer, StaticAnswer
from user import UserManager

db_name = 'sg1'

# set db, user_manager
db = pymongo.MongoClient('127.0.0.1', 27017, connect=False).get_database(db_name)
sys.modules['feature'].__dict__['db'] = db
sys.modules['feature'].__dict__['user_manager'] = UserManager(db.user)
# load model
model = pickle.load(open('data/model_0315.pkl', 'rb'))
print(model)


def evaluate_follow():
    all_result = []
    all_target = []
    if os.path.isfile('data/sg1_follow_target.pkl'):
        with open('data/sg1_follow_target.pkl', 'rb') as f:
            all_target = pickle.load(f)
        with open('data/sg1_follow_result.pkl', 'rb') as f:
            all_result = pickle.load(f)
    else:
        for answer_doc in db2.static_sg1.find({}, {'aid': 1, 'tid': 1}):
            answer = StaticAnswer(answer_doc['tid'], answer_doc['aid'])
            answer.load_from_raw()
            answer.build_cand_edges()
            result, target = answer.evaluate_follow()
            all_result.extend(result)
            all_target.extend(target)

        with open('data/sg1_follow_target.pkl', 'wb') as f:
            pickle.dump(all_target, f)

        with open('data/sg1_follow_result.pkl', 'wb') as f:
            pickle.dump(all_result, f)

    args = (all_target, all_result)
    print(metrics.confusion_matrix(*args))
    print(metrics.accuracy_score(*args))


def evaluate_all():
    all_result_edges = []
    all_target_edges = []
    for answer_doc in db2.static_sg1.find({}, {'aid': 1, 'tid': 1}):
        answer = StaticAnswer(answer_doc['tid'], answer_doc['aid'])
        result, target = answer.evaluate_all()
        all_result_edges.extend(result)
        all_target_edges.extend(target)

    predecessor = (
        [e[0] for e in all_target_edges],
        [e[0] for e in all_result_edges],
    )
    reltype = (
        [e[2].value for e in all_target_edges],  # use Enum's value
        [e[2].value for e in all_result_edges],
    )
    pre_and_rel = (
        [e[0] + str(e[2]) for e in all_target_edges],
        [e[0] + str(e[2]) for e in all_result_edges],
    )
    print(metrics.accuracy_score(*predecessor))
    print(metrics.accuracy_score(*reltype))
    print(metrics.accuracy_score(*pre_and_rel))


if __name__ == '__main__':
    # evaluate_follow()
    evaluate_all()