import sys
import pickle
import pymongo
import os.path
from sklearn import metrics
import graphsim as gs

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
        for answer_doc in db2.static_test.find({}, {'aid': 1, 'tid': 1}):
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
    """
    已经排除了只有一个 answerer 的答案
    """
    all_result_edges = []
    all_result_edges_each_answer = []
    all_target_edges = []
    all_target_edges_each_answer = []
    for answer_doc in db2.static_test.find({}, {'aid': 1, 'tid': 1}):
        if answer_doc['aid'] == '87473698':
            continue
        answer = StaticAnswer(answer_doc['tid'], answer_doc['aid'])
        result, target = answer.evaluate_all()
        all_result_edges.extend(result)
        all_result_edges_each_answer.append(result)
        all_target_edges.extend(target)
        all_target_edges_each_answer.append(target)

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

    RTA = []
    RA = []
    SA = []
    for result, target in zip(all_result_edges_each_answer, all_target_edges_each_answer):
        if len(result) == 0:
            continue

        assert len(result) == len(target)
        N = len(result)
        correct_RTA = correct_RA = correct_SA = 0
        for r, t in zip(result, target):
            if r[0] == t[0]:
                correct_SA += 1
            if r[2].value == t[2].value:
                correct_RTA += 1
            if r[0] == t[0] and r[2].value == t[2].value:
                correct_RA += 1
        RTA.append(correct_RTA/N)
        RA.append(correct_RA/N)
        SA.append(correct_SA/N)

    print("mean RTA" + str(sum(RTA)/len(RTA)))
    print("mean SA" + str(sum(SA)/len(SA)))
    print("mean RA" + str(sum(RA)/len(RA)))

    with open('data/fuck.pkl', 'wb') as f:
        pickle.dump({
            'RTA': RTA,
            'SA': SA,
            'RA': RA
        }, f)

if __name__ == '__main__':
    evaluate_follow()
    evaluate_all()
