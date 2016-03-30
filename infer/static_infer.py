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

# sqa
tid='19553298'
qid="40617404"
aid="87423946"
sqa = StaticQuestionWithAnswer(tid, qid)
collection = db.get_collection(a_col(tid))

# get answers, invoke answer.infer_preparation
answers = []
for answer_doc in collection.find({'qid': qid}, {'aid': 1}):
    answer = StaticAnswer(tid, answer_doc['aid'])
    answer.load_from_dynamic()
    answer.infer_preparation(sqa)
    answers.append(answer)

# fill follower
sqa.fill_question_follower_time()

# load model
model = pickle.load(open('data/model.pkl', 'rb'))
print(model)

# infer
for answer in answers:
    if answer.aid == aid:
        answer.infer(model=model)
