from client import client
from datetime import datetime
from pymongo import MongoClient

db = MongoClient('127.0.0.1:27017').zhihu_data
answers = list(db['19551147_a'].find({'qid': '40566262'}).sort([('time', -1)]))
#
url = 'https://www.zhihu.com/question/40566262?sort=created'
question = client.question(url)
i = 0

for answer in question.answers:
    if answer.creation_time < datetime(2016, 2, 20, 15, 8, 0):
        # if answer.author.id == answers[i]['answerer'] and\
        if answer.creation_time == answers[i]['time']:
            print(answer.author.id, answer.creation_time)
            i += 1
        else:
            print('miss: ', answer.author.id, answer.creation_time)
