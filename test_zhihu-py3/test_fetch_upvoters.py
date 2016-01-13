# coding: utf-8
from client import client

ans_url = 'https://www.zhihu.com/question/39451817/answer/81393872'

ans = client.answer(ans_url)

for upvoter in ans.upvoters:
    print(upvoter.name, upvoter.upvote_num, upvoter.thank_num,
         upvoter.question_num, upvoter.answer_num)