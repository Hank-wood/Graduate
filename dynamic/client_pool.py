import os
import logging

from zhihu import ZhihuClient
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPProxyAuth

from common import test_cookie, ROOT
from utils import validate_cookie

logger = logging.getLogger(__name__)


class _ClientPool:
    proxies = ['114.215.174.98:16816']

    def __init__(self):
        self.index = 0
        self.clients = []
        self.POOL_SIZE = 0

    def add_client(self, client, location=None):
        # client._session.mount('https://www.zhihu.com',
        #                       HTTPAdapter(pool_connections=1,
        #                                   pool_maxsize=1000))
        client.set_proxy_pool(self.proxies)
        self.clients.append(client)
        self.POOL_SIZE += 1

    def get_next_client(self):
        self.index = (self.index + 1) % self.POOL_SIZE
        return self.clients[self.index]

pool1 = _ClientPool()
pool2 = _ClientPool()
for cookie in os.listdir(os.path.join(ROOT, 'cookies')):
    if validate_cookie(os.path.join(ROOT, 'cookies', cookie)):
        logger.info('cookie %s is valid' % cookie)
        print('cookie %s is valid' % cookie)
    else:
        logger.error('cookie %s is invalid' % cookie)
        print('cookie %s is invalid' % cookie)

    client1 = ZhihuClient(os.path.join(ROOT, 'cookies', cookie))
    pool1.add_client(client1)
    client2 = ZhihuClient(os.path.join(ROOT, 'cookies', cookie))
    pool2.add_client(client2)


def get_client():
    return pool1.get_next_client()


def get_client2():
    return pool2.get_next_client()


test_client = ZhihuClient(test_cookie)
def get_client_test():
    return test_client
