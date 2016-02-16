from functools import partialmethod
from requests import Session

class T:
    def test(self, msg=''):
        print(msg)

    test = partialmethod(test, msg='4444')

Session.get = partialmethod(Session.get, timeout=5)

T().test()
print(Session().get('http://www.baidu.com'))


from client import client
client._session.get('http://10.255.255.1')
