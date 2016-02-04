import zhihu
from common import test_cookie


_client1 = zhihu.ZhihuClient(test_cookie)


def get_client():
    return _client1