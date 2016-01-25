from client import client
import time


user = client.author('https://www.zhihu.com/people/laike9m')

start = time.time()

for i, follower in enumerate(user.followers):
    # time.sleep(0.1)
    print(i)

end = time.time()

print("execution time: %d" % (end - start))