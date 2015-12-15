from client import client

question = client.Question('http://www.zhihu.com/question/38537304')

print(question.answer_num)

data = {'_xsrf': question.xsrf, 'offset': '40'}
res = question._session.post('https://www.zhihu.com/question/38299997/log', data=data)
# res = question._session.post('https://www.zhihu.com/question/38537304/log', data=data)

from pprint import pprint
pprint(res.json())
