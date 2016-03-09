import os
import logging

from zhihu import ZhihuClient
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPProxyAuth

from common import test_cookie, ROOT
from utils import validate_cookie

logger = logging.getLogger(__name__)


class _ClientPool:
    auth_mesh = HTTPProxyAuth('laike9m', '123')
    proxies_mesh = [
        # 'http://45.32.11.96:31280',
        'http://188.166.232.186:31280'
    ]
    proxies_kunpeng = [
        'http://laike9m:123@124.42.118.223:8088',
        'http://laike9m:123@115.47.37.115:8088',
        'http://laike9m:123@221.122.152.206:8088',
        'http://laike9m:123@221.122.154.229:8088',
        'http://laike9m:123@221.122.154.233:8088',
        'http://laike9m:123@221.122.154.153:8088',
        'http://laike9m:123@119.61.19.39:8088',
        'http://laike9m:123@106.0.4.196:8088',
        'http://laike9m:123@113.59.227.65:8088',
        'http://laike9m:123@114.113.109.20:8088',
    ]

    def __init__(self):
        self.index = 0
        self.clients = []
        self.POOL_SIZE = 0

    def add_client(self, client, type):
        client._session.mount('https://www.zhihu.com',
                              HTTPAdapter(pool_connections=1,
                                          pool_maxsize=1000))
        if type == 'mesh':
            client.set_proxy_pool(self.proxies_mesh, auth=self.auth_mesh,
                                  https=False)
        elif type == 'kunpeng':
            client.set_proxy_pool(self.proxies_kunpeng)
        else:
            raise Exception("no such proxy type" + type)
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
    pool1.add_client(client1, 'mesh')
    client2 = ZhihuClient(os.path.join(ROOT, 'cookies', cookie))
    pool2.add_client(client2, 'kunpeng')


def get_client():
    return pool1.get_next_client()


def get_client2():
    return pool2.get_next_client()


def get_client_test():
    return ZhihuClient(test_cookie)
