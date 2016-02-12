def gen():
    for i in range(10):
        try:
            if i == 5:
                yield 1/0
            else:
                yield i
        except:
            yield 'ANA'

p = list(gen())
assert p == [0, 1, 2, 3, 4, 'ANA', 6, 7, 8, 9]