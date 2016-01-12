from client import client
import requests

url = 'https://www.zhihu.com/question/39389254'
question = client.question(url)

print(question.creation_time)


url = 'https://www.zhihu.com/question/39416522'
# question = client.question(url)
# print(question.answer_num)

r = requests.get(url)
print(r.content)

url = 'https://www.zhihu.com/question/39271193/answer/80747935'
r = requests.get(url)
print(r.status_code)
