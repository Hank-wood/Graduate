import requests
from requests.adapters import HTTPAdapter
from threading import Thread
import logging

logging.basicConfig(filename='out.txt', level=logging.DEBUG, filemode='w')
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True


def test_session_close():
    s = requests.Sessio()
    class B:
        def __init__(self, session):
            self._session = session

        def get(self):
            r = self._session.get('http://www.baidu.com')
            print(r.status_code)


    b1 = B(s)
    b2 = B(s)

    b1.get()
    b1._session.close()
    b2.get()


def test_pool_connections():
    # 测试访问 zhihu.com 和 zhihu.com/question/xxx 不会新建 connection
    s = requests.Session()
    s.mount('https://www.zhihu.com', HTTPAdapter(pool_connections=1))
    s.get('https://www.zhihu.com/question/36612174')
    s.get('https://www.zhihu.com')
    """output
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): www.zhihu.com
    DEBUG:requests.packages.urllib3.connectionpool:"GET /question/36612174 HTTP/1.1" 200 21854
    DEBUG:requests.packages.urllib3.connectionpool:"GET / HTTP/1.1" 200 2623
    """

    logging.getLogger().info('----------------------------------------')

    # 测试访问不同 host 会新建两个 connection
    s = requests.Session()
    s.mount('https://', HTTPAdapter(pool_connections=1))
    s.get('https://www.baidu.com')
    s.get('https://www.zhihu.com')
    s.get('https://www.baidu.com')
    """output
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): www.baidu.com
    DEBUG:requests.packages.urllib3.connectionpool:"GET / HTTP/1.1" 200 None
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): www.zhihu.com
    DEBUG:requests.packages.urllib3.connectionpool:"GET / HTTP/1.1" 200 2621
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): www.baidu.com
    DEBUG:requests.packages.urllib3.connectionpool:"GET / HTTP/1.1" 200 None
    """
    logging.getLogger().info('----------------------------------------')

    # 测试 pool_connection 对连接的缓存
    s = requests.Session()
    s.mount('https://', HTTPAdapter(pool_connections=2))
    s.get('https://www.baidu.com')
    s.get('https://www.zhihu.com')
    s.get('https://www.baidu.com')
    """output
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): www.baidu.com
    DEBUG:requests.packages.urllib3.connectionpool:"GET / HTTP/1.1" 200 None
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): www.zhihu.com
    DEBUG:requests.packages.urllib3.connectionpool:"GET / HTTP/1.1" 200 2623
    DEBUG:requests.packages.urllib3.connectionpool:"GET / HTTP/1.1" 200 None
    """
    logging.getLogger().info('----------------------------------------')


def test_pool_max_size():
    # 测试 pool_maxsize 对多线程访问的影响
    def thread_get(url):
        s.get(url)

    s = requests.Session()
    s.mount('https://', HTTPAdapter(pool_connections=1, pool_maxsize=1))
    t1 = Thread(target=thread_get, args=('https://www.zhihu.com',))
    t2 = Thread(target=thread_get, args=('https://www.zhihu.com/question/36612174',))
    t1.start()
    t2.start()
    t1.join();t2.join()
    t3 = Thread(target=thread_get, args=('https://www.zhihu.com/question/39420364',))
    t4 = Thread(target=thread_get, args=('https://www.zhihu.com/question/21362402',))
    t3.start();t4.start()
    t3.join();t4.join()
    """
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): www.zhihu.com
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (2): www.zhihu.com
    DEBUG:requests.packages.urllib3.connectionpool:"GET /question/36612174 HTTP/1.1" 200 21906
    DEBUG:requests.packages.urllib3.connectionpool:"GET / HTTP/1.1" 200 2606
    WARNING:requests.packages.urllib3.connectionpool:Connection pool is full, discarding connection: www.zhihu.com
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (3): www.zhihu.com
    DEBUG:requests.packages.urllib3.connectionpool:"GET /question/39420364 HTTP/1.1" 200 28739
    DEBUG:requests.packages.urllib3.connectionpool:"GET /question/21362402 HTTP/1.1" 200 57556
    WARNING:requests.packages.urllib3.connectionpool:Connection pool is full, discarding connection: www.zhihu.com
    """
    logging.getLogger().info('----------------------------------------')

    s = requests.Session()
    s.mount('https://', HTTPAdapter(pool_connections=1, pool_maxsize=2))
    t1 = Thread(target=thread_get, args=('https://www.zhihu.com',))
    t2 = Thread(target=thread_get, args=('https://www.zhihu.com/question/36612174',))
    t1.start()
    t2.start()
    t1.join();t2.join()
    t3 = Thread(target=thread_get, args=('https://www.zhihu.com/question/39420364',))
    t4 = Thread(target=thread_get, args=('https://www.zhihu.com/question/21362402',))
    t3.start();t4.start()
    """
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): www.zhihu.com
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (2): www.zhihu.com
    DEBUG:requests.packages.urllib3.connectionpool:"GET /question/36612174 HTTP/1.1" 200 21906
    DEBUG:requests.packages.urllib3.connectionpool:"GET / HTTP/1.1" 200 2606
    DEBUG:requests.packages.urllib3.connectionpool:"GET /question/21362402 HTTP/1.1" 200 57556
    DEBUG:requests.packages.urllib3.connectionpool:"GET /question/39420364 HTTP/1.1" 200 28739
    """


def test_mount_prefix():
    # 测试 HTTPAdapter 是相互独立的
    def thread_get(url):
        s.get(url)

    s = requests.Session()
    s.mount('https://', HTTPAdapter(pool_connections=1, pool_maxsize=2))
    s.mount('https://baidu.com', HTTPAdapter(pool_connections=1, pool_maxsize=1))
    t1 = Thread(target=thread_get, args=('https://www.zhihu.com',))
    t2 =Thread(target=thread_get, args=('https://www.zhihu.com/question/36612174',))
    t1.start()
    t2.start()
    t1.join();t2.join()
    t3 = Thread(target=thread_get, args=('https://www.zhihu.com/question/39420364',))
    t4 = Thread(target=thread_get, args=('https://www.zhihu.com/question/21362402',))
    t3.start();t4.start()
    t3.join();t4.join()
    """output
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): www.zhihu.com
    INFO:requests.packages.urllib3.connectionpool:Starting new HTTPS connection (2): www.zhihu.com
    DEBUG:requests.packages.urllib3.connectionpool:"GET /question/36612174 HTTP/1.1" 200 21906
    DEBUG:requests.packages.urllib3.connectionpool:"GET / HTTP/1.1" 200 2623
    DEBUG:requests.packages.urllib3.connectionpool:"GET /question/39420364 HTTP/1.1" 200 28739
    DEBUG:requests.packages.urllib3.connectionpool:"GET /question/21362402 HTTP/1.1" 200 57669
    """


if __name__ == '__main__':
    # test_pool_connections()
    # test_pool_max_size()
    test_mount_prefix()