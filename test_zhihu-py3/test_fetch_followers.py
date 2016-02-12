from client import client
import time


user = client.author('https://www.zhihu.com/people/xu-gong-68-27')
print(user.followee_num)
print(user.follower_num)

start = time.time()

for i, follower in enumerate(user.followers):
    print(i, follower.id)

for i, followee in enumerate(user.followees):
    print(i, followee.id)

end = time.time()

print("execution time: %d" % (end - start))