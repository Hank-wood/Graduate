from client import client


url = 'https://www.zhihu.com/question/40247284/answer/85562106'
answer = client.answer(url)
print(answer.deleted)
answer.refresh()
print(answer.deleted)


url = 'https://www.zhihu.com/question/40185501/answer/85271078'
answer = client.answer(url)
print(answer.deleted)
answer.refresh()
print(answer.deleted)
