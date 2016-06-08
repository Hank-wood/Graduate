from copy import deepcopy
import pytest

from component import DynamicQuestionWithAnswer, DynamicAnswer, UserAction
from datetime import datetime, timedelta
from iutils import *
from icommon import action_table, db2, RelationType


skip = True


def teardown_function(function):
    for collection_name in db2.collection_names():
        if 'system' not in collection_name:
            db2[collection_name].drop()


@pytest.mark.skipif(skip, reason="")
def test_get_closet_users():
    t = datetime(1999, 1, 1, 12, 0, 0)
    flist = []
    assert DynamicQuestionWithAnswer.get_closest_users(flist, t) == []

    flist = [
        {'time': 0, 'uids': ['u1', 'u2']}
    ]
    assert DynamicQuestionWithAnswer.get_closest_users(flist, t) == ['u1', 'u2']

    flist = [
        {'time': t, 'uids': ['u1', 'u2']},
        {'time': t+timedelta(seconds=1), 'uids': ['u3', 'u4']}
    ]
    assert DynamicQuestionWithAnswer.get_closest_users(flist, t) == ['u1', 'u2']

    flist = [
        {'time': t-timedelta(seconds=1), 'uids': ['u1', 'u2']},
        {'time': t, 'uids': ['u3', 'u4']}
    ]
    assert DynamicQuestionWithAnswer.get_closest_users(flist, t) == ['u1', 'u2', 'u3', 'u4']

    flist = [
        {'time': t-timedelta(seconds=1), 'uids': ['u1', 'u2']},
        {'time': t, 'uids': ['u3', 'u4']},
        {'time': t+timedelta(seconds=1), 'uids': ['u5', 'u6']}
    ]
    assert DynamicQuestionWithAnswer.get_closest_users(flist, t) == ['u1', 'u2', 'u3', 'u4']

    flist = [
        {'time': t-timedelta(seconds=2), 'uids': ['u1', 'u2']},
        {'time': t-timedelta(seconds=1), 'uids': ['u3', 'u4']},
        {'time': t+timedelta(seconds=2), 'uids': ['u5', 'u6']}
    ]
    assert DynamicQuestionWithAnswer.get_closest_users(flist, t) == ['u1', 'u2', 'u3', 'u4']

    flist = [
        {'time': t-timedelta(seconds=3), 'uids': ['u1', 'u2']},
        {'time': t-timedelta(seconds=2), 'uids': ['u3', 'u4']},
        {'time': t+timedelta(seconds=1), 'uids': ['u5', 'u6']}
    ]
    assert DynamicQuestionWithAnswer.get_closest_users(flist, t) == \
           ['u1', 'u2', 'u3', 'u4', 'u5', 'u6']

    flist = [
        {'time': t-timedelta(seconds=2), 'uids': ['u1', 'u2']},
        {'time': t-timedelta(seconds=1), 'uids': ['u3', 'u4']},
        {'time': t+timedelta(seconds=0.5), 'uids': ['u5', 'u6']},
        {'time': t+timedelta(seconds=3), 'uids': ['u7', 'u8']}
    ]
    assert DynamicQuestionWithAnswer.get_closest_users(flist, t) == \
           ['u1', 'u2', 'u3', 'u4', 'u5', 'u6']


@pytest.mark.skipif(skip, reason="")
def test_interpolate():
    t = datetime(1999, 1, 1, 12, 0, 0)
    useraction_list = [
        UserAction(t, 'a1', 'u1', ''),
        UserAction(t+timedelta(seconds=1), 'a1', 'u2', ''),
    ]
    ori = useraction_list.copy()
    interpolate(useraction_list)
    assert ori == useraction_list

    useraction_list = [
        UserAction(None, 'a1', 'u1', ''),
        UserAction(t+timedelta(seconds=1), 'a1', 'u2', ''),
    ]
    interpolate(useraction_list)
    assert useraction_list == [
        UserAction(t+timedelta(seconds=1), 'a1', 'u1', ''),
        UserAction(t+timedelta(seconds=1), 'a1', 'u2', ''),
    ]

    useraction_list = [
        UserAction(t, 'a1', 'u1', ''),
        UserAction(None, 'a1', 'u2', ''),
    ]
    interpolate(useraction_list)
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
    interpolate(useraction_list)
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
    interpolate(useraction_list)
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
    interpolate(useraction_list)
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


@pytest.mark.skipif(skip, reason="")
def test_get_action_type():
    for key in action_table.keys():
        assert acttype2str(key) == action_table[key]

    assert acttype2str(0b100001) == 'ASK_QUESTION,COLLECT_ANSWER'
    assert acttype2str(0b000110) == 'FOLLOW_QUESTION,ANSWER_QUESTION'
    assert acttype2str(0b011000) == 'UPVOTE_ANSWER,COMMENT_ANSWER'

    assert acttype2str(0b011100) == \
        'ANSWER_QUESTION,UPVOTE_ANSWER,COMMENT_ANSWER'
    assert acttype2str(0b101001) == \
        'ASK_QUESTION,UPVOTE_ANSWER,COLLECT_ANSWER'
    assert acttype2str(0b111111) == \
        'ASK_QUESTION,FOLLOW_QUESTION,ANSWER_QUESTION,UPVOTE_ANSWER,COMMENT_ANSWER,COLLECT_ANSWER'


def test_transform():
    """
    测试 RelationType 存储进 mongodb 和读取
    """
    data = {'some': 1, 'links': [{'reltype': RelationType.follow, 'v': 1}]}
    db2.dynamic_train.insert(deepcopy(data))
    assert db2.dynamic_train.find_one({'some': 1}, {'_id': 0}) == data
    data = {'some': 2, 'links': [
        {'reltype': RelationType.follow, 'v': 1},
        {'reltype': RelationType.qlink, 'v': 1},
        {'reltype': RelationType.notification, 'v': 1},
        {'reltype': RelationType.recommendation, 'v': 1}
    ]}
    db2.dynamic_train.insert(deepcopy(data))
    assert db2.dynamic_train.find_one({'some': 2}, {'_id': 0}) == data
