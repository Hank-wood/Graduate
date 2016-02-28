from client import client
from common import *
from zhihu import ActType

question = client.question('https://www.zhihu.com/question/40799298')

for _, follower in zip(range(10), question.followers):
    if follower is ANONYMOUS:
        continue
    print(follower.id)

"""
answerers = set()
qid = '40138173'
for answer in question.answers:
    answerers.add(answer.author.id)

for follower in question.followers:
    if follower is ANONYMOUS:
        continue
    elif follower.id not in answerers:
        print(follower.id)
        for i, act in enumerate(follower.activities):
            if act.type == ActType.FOLLOW_QUESTION and str(act.content.id) == qid:
                break
            if i > 10:
                print('no such act: ' + follower.id)
                break
"""