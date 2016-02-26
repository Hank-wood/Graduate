from collections import namedtuple
from queue import PriorityQueue


Car = namedtuple('Car', ['type', 'speed', 'weight'])
c1 = Car(1, 2, 100)
c2 = Car(1, 3, 200)
c3 = Car(1, 3, 300)
q = PriorityQueue()
q.put(c3)
q.put(c1)
q.put(c2)
while not q.empty():
    print(q.get())


# 证明 pq 可以作用域 namedtuple