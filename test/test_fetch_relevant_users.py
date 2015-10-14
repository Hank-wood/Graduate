# coding: utf-8

"""
把一个问题里所有关注/评论/点赞/回答的人收集起来
"""

import time
import requests
from client import client

# 那些曾经轰动一时的新闻事件，都有哪些后续发展？
question_url = 'http://www.zhihu.com/question/36218460'

user_collection = set()

question = client.question(question_url)
cnt = 0
all = 0
for answer in question.answers:
    answer.client = client
    user_collection.add(answer.author)
    for upvoter in answer.upvoters:
        cnt += 1
        user_collection.add(upvoter.name)
        print(cnt)
        # TODO: 关键是替换 session


print(cnt)