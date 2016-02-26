from component import InfoStorage
from datetime import datetime, timedelta


def test_get_closet_users():
    time = datetime(1999, 1, 1, 12, 0, 0)
    flist = []
    assert InfoStorage.get_closest_users(flist, time) == []

    flist = [
        {'time': 0, 'uids': ['u1', 'u2']}
    ]
    assert InfoStorage.get_closest_users(flist, time) == ['u1', 'u2']

    flist = [
        {'time': time, 'uids': ['u1', 'u2']},
        {'time': time+timedelta(seconds=1), 'uids': ['u3', 'u4']}
    ]
    assert InfoStorage.get_closest_users(flist, time) == ['u1', 'u2']

    flist = [
        {'time': time-timedelta(seconds=1), 'uids': ['u1', 'u2']},
        {'time': time, 'uids': ['u3', 'u4']}
    ]
    assert InfoStorage.get_closest_users(flist, time) == ['u1', 'u2', 'u3', 'u4']

    flist = [
        {'time': time-timedelta(seconds=1), 'uids': ['u1', 'u2']},
        {'time': time, 'uids': ['u3', 'u4']},
        {'time': time+timedelta(seconds=1), 'uids': ['u5', 'u6']}
    ]
    assert InfoStorage.get_closest_users(flist, time) == ['u1', 'u2', 'u3', 'u4']

    flist = [
        {'time': time-timedelta(seconds=2), 'uids': ['u1', 'u2']},
        {'time': time-timedelta(seconds=1), 'uids': ['u3', 'u4']},
        {'time': time+timedelta(seconds=2), 'uids': ['u5', 'u6']}
    ]
    assert InfoStorage.get_closest_users(flist, time) == ['u1', 'u2', 'u3', 'u4']

    flist = [
        {'time': time-timedelta(seconds=3), 'uids': ['u1', 'u2']},
        {'time': time-timedelta(seconds=2), 'uids': ['u3', 'u4']},
        {'time': time+timedelta(seconds=1), 'uids': ['u5', 'u6']}
    ]
    assert InfoStorage.get_closest_users(flist, time) == \
           ['u1', 'u2', 'u3', 'u4', 'u5', 'u6']

    flist = [
        {'time': time-timedelta(seconds=2), 'uids': ['u1', 'u2']},
        {'time': time-timedelta(seconds=1), 'uids': ['u3', 'u4']},
        {'time': time+timedelta(seconds=0.5), 'uids': ['u5', 'u6']},
        {'time': time+timedelta(seconds=3), 'uids': ['u7', 'u8']}
    ]
    assert InfoStorage.get_closest_users(flist, time) == \
            ['u1', 'u2', 'u3', 'u4', 'u5', 'u6']
