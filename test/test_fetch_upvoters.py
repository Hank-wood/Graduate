from zhihu import ZhihuClient
from settings import cookie

client = ZhihuClient(cookie)
ans_url = 'http://www.zhihu.com/question/35107886/answer/61219684'

ans = client.answer(ans_url)

for upvoter in ans.upvoters:
    print(upvoter.name, upvoter.upvote_num, upvoter.thank_num,
         upvoter.question_num, upvoter.answer_num)