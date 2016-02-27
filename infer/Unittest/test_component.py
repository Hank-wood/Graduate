from component import InfoStorage, Answer, UserAction
from datetime import datetime, timedelta

import pytest

skip = True


@pytest.mark.skipif(skip, reason="")
def test_get_closet_users():
    t = datetime(1999, 1, 1, 12, 0, 0)
    flist = []
    assert InfoStorage.get_closest_users(flist, t) == []

    flist = [
        {'time': 0, 'uids': ['u1', 'u2']}
    ]
    assert InfoStorage.get_closest_users(flist, t) == ['u1', 'u2']

    flist = [
        {'time': t, 'uids': ['u1', 'u2']},
        {'time': t+timedelta(seconds=1), 'uids': ['u3', 'u4']}
    ]
    assert InfoStorage.get_closest_users(flist, t) == ['u1', 'u2']

    flist = [
        {'time': t-timedelta(seconds=1), 'uids': ['u1', 'u2']},
        {'time': t, 'uids': ['u3', 'u4']}
    ]
    assert InfoStorage.get_closest_users(flist, t) == ['u1', 'u2', 'u3', 'u4']

    flist = [
        {'time': t-timedelta(seconds=1), 'uids': ['u1', 'u2']},
        {'time': t, 'uids': ['u3', 'u4']},
        {'time': t+timedelta(seconds=1), 'uids': ['u5', 'u6']}
    ]
    assert InfoStorage.get_closest_users(flist, t) == ['u1', 'u2', 'u3', 'u4']

    flist = [
        {'time': t-timedelta(seconds=2), 'uids': ['u1', 'u2']},
        {'time': t-timedelta(seconds=1), 'uids': ['u3', 'u4']},
        {'time': t+timedelta(seconds=2), 'uids': ['u5', 'u6']}
    ]
    assert InfoStorage.get_closest_users(flist, t) == ['u1', 'u2', 'u3', 'u4']

    flist = [
        {'time': t-timedelta(seconds=3), 'uids': ['u1', 'u2']},
        {'time': t-timedelta(seconds=2), 'uids': ['u3', 'u4']},
        {'time': t+timedelta(seconds=1), 'uids': ['u5', 'u6']}
    ]
    assert InfoStorage.get_closest_users(flist, t) == \
           ['u1', 'u2', 'u3', 'u4', 'u5', 'u6']

    flist = [
        {'time': t-timedelta(seconds=2), 'uids': ['u1', 'u2']},
        {'time': t-timedelta(seconds=1), 'uids': ['u3', 'u4']},
        {'time': t+timedelta(seconds=0.5), 'uids': ['u5', 'u6']},
        {'time': t+timedelta(seconds=3), 'uids': ['u7', 'u8']}
    ]
    assert InfoStorage.get_closest_users(flist, t) == \
            ['u1', 'u2', 'u3', 'u4', 'u5', 'u6']


def test_interpolate():
    t = datetime(1999, 1, 1, 12, 0, 0)
    useraction_list = [
        UserAction(t, 'a1', 'u1', ''),
        UserAction(t+timedelta(seconds=1), 'a1', 'u2', ''),
    ]
    ori = useraction_list.copy()
    Answer.interpolate(useraction_list)
    assert ori == useraction_list

    useraction_list = [
        UserAction(None, 'a1', 'u1', ''),
        UserAction(t+timedelta(seconds=1), 'a1', 'u2', ''),
    ]
    Answer.interpolate(useraction_list)
    assert useraction_list == [
        UserAction(t+timedelta(seconds=1), 'a1', 'u1', ''),
        UserAction(t+timedelta(seconds=1), 'a1', 'u2', ''),
    ]

    useraction_list = [
        UserAction(t, 'a1', 'u1', ''),
        UserAction(None, 'a1', 'u2', ''),
    ]
    Answer.interpolate(useraction_list)
    assert useraction_list == [
        UserAction(t, 'a1', 'u1', ''),
        UserAction(t, 'a1', 'u2', ''),
    ]

    useraction_list = [
        UserAction(None, 'a1', 'u1', ''),
        UserAction(None, 'a1', 'u2', ''),
        UserAction(t, 'a1', 'u3', ''),
        UserAction(t+timedelta(seconds=1), 'a1', 'u4', ''),
        UserAction(None, 'a1', 'u5', ''),
        UserAction(None, 'a1', 'u6', ''),
    ]
    Answer.interpolate(useraction_list)
    assert useraction_list == [
        UserAction(t, 'a1', 'u1', ''),
        UserAction(t, 'a1', 'u2', ''),
        UserAction(t, 'a1', 'u3', ''),
        UserAction(t+timedelta(seconds=1), 'a1', 'u4', ''),
        UserAction(t+timedelta(seconds=1), 'a1', 'u5', ''),
        UserAction(t+timedelta(seconds=1), 'a1', 'u6', ''),
    ]

    useraction_list = [
        UserAction(t, 'a1', 'u1', ''),
        UserAction(None, 'a1', 'u2', ''),
        UserAction(None, 'a1', 'u3', ''),
        UserAction(t+timedelta(seconds=1.2), 'a1', 'u4', ''),
    ]
    Answer.interpolate(useraction_list)
    assert useraction_list == [
        UserAction(t, 'a1', 'u1', ''),
        UserAction(t+timedelta(seconds=0.4), 'a1', 'u2', ''),
        UserAction(t+timedelta(seconds=0.8), 'a1', 'u3', ''),
        UserAction(t+timedelta(seconds=1.2), 'a1', 'u4', ''),
    ]

    useraction_list = [
        UserAction(None, 'a1', 'u-1', ''),
        UserAction(None, 'a1', 'u0', ''),
        UserAction(t, 'a1', 'u1', ''),
        UserAction(None, 'a1', 'u2', ''),
        UserAction(None, 'a1', 'u3', ''),
        UserAction(t+timedelta(seconds=1.2), 'a1', 'u4', ''),
        UserAction(None, 'a1', 'u5', ''),
        UserAction(None, 'a1', 'u6', ''),
    ]
    Answer.interpolate(useraction_list)
    assert useraction_list == [
        UserAction(t, 'a1', 'u-1', ''),
        UserAction(t, 'a1', 'u0', ''),
        UserAction(t, 'a1', 'u1', ''),
        UserAction(t+timedelta(seconds=0.4), 'a1', 'u2', ''),
        UserAction(t+timedelta(seconds=0.8), 'a1', 'u3', ''),
        UserAction(t+timedelta(seconds=1.2), 'a1', 'u4', ''),
        UserAction(t+timedelta(seconds=1.2), 'a1', 'u5', ''),
        UserAction(t+timedelta(seconds=1.2), 'a1', 'u6', ''),
    ]

