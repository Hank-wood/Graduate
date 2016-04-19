"""
抓取没有follower or followee的, 从当前目录下的 tobe_fetch.txt 提取
"""
import re
from client import client
from user import UserManager
import pymongo


db = pymongo.MongoClient('127.0.0.1', 27017).get_database('zhihu_data_0315')
user_col = db.user
user_manager = UserManager(db.user)

with open('tobe_fetch.txt') as f:
    lines = f.readlines()

user_lack_follower = []
user_lack_followee = []

pattern = re.compile(r'([^\s]+)\slacks follower,([^\s]+)\s')
for line in lines:
    obj = pattern.search(line)
    user_lack_follower.append(obj.group(1))
    user_lack_followee.append(obj.group(2))

for er, ee in zip(user_lack_follower, user_lack_followee):
    u1 = client.Author('https://www.zhihu.com/people/' + ee)
    u2 = client.Author('https://www.zhihu.com/people/' + er)
    if u1.followee_num < u2.follower_num:
        udoc = user_col.find_one({'uid': ee})
        assert udoc is not None
        if 'followee' in udoc:
            print("skip " + ee)
            continue
        print("fetch " + ee)
        followees = user_manager.fetch_user_followee(u1)
    else:
        udoc = user_col.find_one({'uid': er})
        assert udoc is not None
        if 'follower' in udoc:
            print("skip " + er)
            continue
        print("fetch " + er)
        followers = user_manager.fetch_user_follower(u2)


