from client import client
from zhihu import ANONYMOUS

user = client.author('https://www.zhihu.com/people/leng-ying-26')
uids = [ee.id for ee in user.followees if ee is not ANONYMOUS]
print(uids)
