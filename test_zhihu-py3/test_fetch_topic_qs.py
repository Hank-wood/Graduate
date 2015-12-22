# coding: utf-8
from client import client

ans_url = 'https://www.zhihu.com/topic/19552330/'

topic = client.topic(ans_url)

for _, q in zip(range(10), topic.questions):
    print(q.title)
