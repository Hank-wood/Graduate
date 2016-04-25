import sys
import pickle
import pymongo

from iutils import *
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

for collection_name in db.collection_names():
    if not is_q_col(collection_name):
        continue
    q_collection = db[collection_name]
    a_collection = db[q_to_a(collection_name)]
    for q_doc in q_collection.find({}, {'qid':1, 'topic':1}):
        qid = q_doc['qid']
        tid = collection_name[:-2]
        sqa = StaticQuestionWithAnswer(tid, qid)
        collection = db.get_collection(a_col(tid))

        # get answers, invoke answer.infer_preparation
        answers = []
        for answer_doc in a_collection.find({'qid': qid}, {'aid': 1}):
            answer = StaticAnswer(tid, answer_doc['aid'])
            # 如果没有侯选边,就不推断
            answer.load_from_dynamic()
            answer.infer_preparation(sqa)
            answers.append(answer)

        # fill follower
        sqa.fill_question_follower_time()

        # infer
        for answer in answers:
            answer.infer(model=model)
