from client import client
from zhihu import ANONYMOUS
from pprint import pprint


answer = client.answer('https://www.zhihu.com/question/40601601/answer/87377293')
# for comment in answer.latest_comments:
#     print(comment.author.id)

new_commenters = {}
for comment in answer.latest_comments:
    if comment.author is ANONYMOUS:
        continue
    else:
        new_commenters[comment.author.id] = {
            'uid': comment.author.id,
            'time': comment.creation_time,
            'cid': comment.cid
        }
if new_commenters:
    new_commenters = list(new_commenters.values())
    new_commenters.sort(key=lambda x: x['time'])

pprint(new_commenters)
