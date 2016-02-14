from client import client
import requests

url = 'https://www.zhihu.com/question/39389254'
question = client.question(url)
print(question.topics)
