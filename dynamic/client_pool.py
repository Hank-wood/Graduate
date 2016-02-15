import os

from zhihu import ZhihuClient
from requests.adapters import HTTPAdapter, Retry

from common import test_cookie, ROOT


class _ClientPool:
    def __init__(self):
        self.index = 0
        self.clients = []
        self.POOL_SIZE = 0

    def add_client(self, client):
        client._session.mount('https://www.zhihu.com',
                              HTTPAdapter(pool_connections=1,
                                          pool_maxsize=1000,
                                          max_retries=Retry(100)))
        self.clients.append(client)
        self.POOL_SIZE += 1

    def get_next_client(self):
        self.index = (self.index + 1) % self.POOL_SIZE
        return self.clients[self.index]

pool = _ClientPool()
for cookie in os.listdir(os.path.join(ROOT, 'cookies')):
    client = ZhihuClient(os.path.join(ROOT, 'cookies', test_cookie))
    pool.add_client(client)

def get_client():
    return pool.get_next_client()
