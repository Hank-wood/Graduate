from zhihu import ActType

ANSWER_QUESTION = ActType.ANSWER_QUESTION.value
UPVOTE_ANSWER = ActType.UPVOTE_ANSWER.value
ASK_QUESTION = ActType.ASK_QUESTION.value
FOLLOW_QUESTION = ActType.FOLLOW_QUESTION.value

ROOT = os.path.dirname(os.path.dirname(__file__))


class FetchTypeError(Exception):
    pass
