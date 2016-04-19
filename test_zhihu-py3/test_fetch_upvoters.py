# coding: utf-8
from client import client
from zhihu import ANONYMOUS
import time

ans_url = 'https://www.zhihu.com/question/42001133/answer/93218150'

ans = client.answer(ans_url)

with open('upvoters.txt', 'w') as f:
    for upvoter in ans.upvoters:
        time.sleep(0.01)
        if upvoter is not ANONYMOUS:
            f.write(upvoter.id + '\n')
