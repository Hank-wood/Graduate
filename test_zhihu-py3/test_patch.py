from unittest.mock import patch, Mock


m = Mock(a=Mock(b=1), c=2)

print(m.a, m.a.b, m.c)
