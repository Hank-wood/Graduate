import os
import logging

from zhihu import ZhihuClient
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPProxyAuth

from common import test_cookie, ROOT
from utils import validate_cookie

logger = logging.getLogger(__name__)


class _ClientPool:
    auth = HTTPProxyAuth('laike9m', '123')
    proxies = {'http': '162.213.39.201:31280'}  # us-ca

    def __init__(self):
        self.index = 0
        self.clients = []
        self.POOL_SIZE = 0

    def add_client(self, client):
        client._session.mount('https://www.zhihu.com',
                              HTTPAdapter(pool_connections=1,
                                          pool_maxsize=1000))
        client._session.auth = self.auth
        client._session.proxies = self.proxies
        self.clients.append(client)
        self.POOL_SIZE += 1

    def get_next_client(self):
        self.index = (self.index + 1) % self.POOL_SIZE
        return self.clients[self.index]

pool = _ClientPool()
for cookie in os.listdir(os.path.join(ROOT, 'cookies')):
    if validate_cookie(os.path.join(ROOT, 'cookies', cookie)):
        logger.info('cookie %s is valid' % cookie)
        # print('cookie %s is valid' % cookie)
    else:
        logger.error('cookie %s is invalid' % cookie)
        # print('cookie %s is invalid' % cookie)

    client = ZhihuClient(os.path.join(ROOT, 'cookies', cookie))
    pool.add_client(client)


def get_client():
    return pool.get_next_client()
