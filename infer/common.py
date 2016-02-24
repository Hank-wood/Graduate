from zhihu import ActType
from pymongo import MongoClient

ANSWER_QUESTION = ActType.ANSWER_QUESTION.value
UPVOTE_ANSWER = ActType.UPVOTE_ANSWER.value
ASK_QUESTION = ActType.ASK_QUESTION.value
FOLLOW_QUESTION = ActType.FOLLOW_QUESTION.value

ROOT = os.path.dirname(os.path.dirname(__file__))

db = MongoClient('127.0.0.1', 27017).zhihu_data


class FetchTypeError(Exception):
    pass
