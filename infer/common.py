from pymongo import MongoClient

ANSWER_QUESTION = 1
UPVOTE_ANSWER = 2
ASK_QUESTION = 3
FOLLOW_QUESTION = 4
COMMENT_ANSWER = 5
COLLECT_ANSWER = 6

ROOT = os.path.dirname(os.path.dirname(__file__))

db = MongoClient('127.0.0.1', 27017).zhihu_data


class FetchTypeError(Exception):
    pass
