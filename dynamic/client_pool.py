import zhihu
from requests.adapters import HTTPAdapter, Retry

from common import test_cookie


_client1 = zhihu.ZhihuClient(test_cookie)
_client1._session.mount('https://www.zhihu.com',
                         HTTPAdapter(pool_connections=1,
                                     pool_maxsize=1000,
                                     max_retries=Retry(100)))


def get_client():
    return _client1