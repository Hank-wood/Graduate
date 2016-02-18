from client import client
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPProxyAuth
import requests


auth = HTTPProxyAuth('laike9m', '123')
proxies = {'http': '162.213.39.201:31280'}
s = requests.Session()
s.auth = auth
s.proxies = proxies
s.cookies = client._session.cookies
resp = s.get('http://www.zhihu.com/people/excited-vczh')
print(resp.text)

# """
client._session.auth = auth
client._session.proxies = proxies

url = 'http://www.zhihu.com/people/excited-vczh'
author = client.author(url)

print('用户名 %s' % author.name)
print('用户简介 %s' % author.motto)
print('用户关注人数 %d' % author.followee_num)
print('取用户粉丝数 %d' % author.follower_num)
print('用户得到赞同数 %d' % author.upvote_num)
print('用户得到感谢数 %d' % author.thank_num)
print('用户提问数 %d' % author.question_num)
print('用户答题数 %d' % author.answer_num)

url = 'http://www.zhihu.com/question/23841579'
question = client.question(url)
for _, answer in zip(range(5), question.answers):
    print(answer.url)
