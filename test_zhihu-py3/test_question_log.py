from client import client


url = 'https://www.zhihu.com/question/39389254'
question = client.question(url)

print(question.creation_time)