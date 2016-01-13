import requests
from requests.adapters import HTTPAdapter

s = requests.Session()
# s.mount('https://', HTTPAdapter(max_retries=5))

class B:
    def __init__(self, session):
        self._session = session

    def get(self):
        r = self._session.get('http://www.baidu.com')
        print(r.status_code)


b1 = B(s)
b2 = B(s)
b3 = B(s)

b1.get()
b1._session.close()
b2.get()
