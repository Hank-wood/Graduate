import sys
from datetime import datetime
from unittest.mock import patch, Mock
from pprint import pprint

import pytest

from icommon import *
from feature import StaticAnswer, TimeRange


@patch('feature.StaticAnswer.has_follow_relation', Mock(return_value=True))
def test_gen_edges():
    aid = '222'
    t1 = datetime(1970,1,1)
    t2 = datetime(1970,1,2)
    t3 = datetime(1970,1,3)
    t4 = datetime(1970,1,4)
    t5 = datetime(1970,1,5)
    t6 = datetime(1970,1,6)
    sys.modules['feature'].__dict__['db'] = {
        '111_a': Mock(find_one=lambda x: {
                    'aid': aid,
                    'time': t1,
                    'answerer': 'u1',
                    'upvoters': [
                        {'uid': 'u2', 'time': None},
                        {'uid': 'u3', 'time': None},
                        {'uid': 'u4', 'time': None},
                        {'uid': 'u5', 'time': None},
                    ],
                    'commenters': [
                        {'uid': 'u2', 'time': t2},
                        {'uid': 'u1', 'time': t4},
                        {'uid': 'u7', 'time': t5}
                    ],
                    'collectors': [
                        {'uid': 'u4', 'time': t3},
                        {'uid': 'u2', 'time': t6}
                    ]
                }
    )}

    sa = StaticAnswer('111', aid)
    sa.load_from_dynamic()
    sa.gen_edges()
    assert sa.cand_edges[0] == \
        FollowEdge(UserAction(t1, aid, 'u1', ANSWER_QUESTION|COMMENT_ANSWER),
                   UserAction(t2, aid, 'u2', UPVOTE_ANSWER|COMMENT_ANSWER|COLLECT_ANSWER))

    assert sa.cand_edges[1] == \
        FollowEdge(UserAction(t1, aid, 'u1', ANSWER_QUESTION|COMMENT_ANSWER),
                   UserAction(TimeRange(t2, t3), aid, 'u3', UPVOTE_ANSWER))

    assert sa.cand_edges[2] == \
        FollowEdge(UserAction(t1, aid, 'u1', ANSWER_QUESTION|COMMENT_ANSWER),
                   UserAction(t3, aid, 'u4', UPVOTE_ANSWER|COLLECT_ANSWER))

    assert sa.cand_edges[3] == \
        FollowEdge(UserAction(t1, aid, 'u1', ANSWER_QUESTION|COMMENT_ANSWER),
                   UserAction(TimeRange(t3), aid, 'u5', UPVOTE_ANSWER))

    assert sa.cand_edges[4] == \
           FollowEdge(UserAction(t1, aid, 'u1', ANSWER_QUESTION|COMMENT_ANSWER),
                      UserAction(t5, aid, 'u7', COMMENT_ANSWER))

    assert sa.cand_edges[5] == \
        FollowEdge(UserAction(t2, aid, 'u2', UPVOTE_ANSWER|COMMENT_ANSWER|COLLECT_ANSWER),
                   UserAction(TimeRange(t2, t3), aid, 'u3', UPVOTE_ANSWER))

    assert sa.cand_edges[6] == \
        FollowEdge(UserAction(t2, aid, 'u2', UPVOTE_ANSWER|COMMENT_ANSWER|COLLECT_ANSWER),
                   UserAction(t3, aid, 'u4', UPVOTE_ANSWER | COLLECT_ANSWER))

    assert sa.cand_edges[7] == \
        FollowEdge(UserAction(t2, aid, 'u2', UPVOTE_ANSWER|COMMENT_ANSWER|COLLECT_ANSWER),
                   UserAction(TimeRange(t3), aid, 'u5', UPVOTE_ANSWER))

    assert sa.cand_edges[8] == \
           FollowEdge(UserAction(t2, aid, 'u2', UPVOTE_ANSWER|COMMENT_ANSWER|COLLECT_ANSWER),
                      UserAction(t5, aid, 'u7', COMMENT_ANSWER))

    assert sa.cand_edges[9] == \
           FollowEdge(UserAction(TimeRange(t2, t3), aid, 'u3', UPVOTE_ANSWER),
                      UserAction(t3, aid, 'u4', UPVOTE_ANSWER|COLLECT_ANSWER))

    assert sa.cand_edges[10] == \
           FollowEdge(UserAction(TimeRange(t2, t3), aid, 'u3', UPVOTE_ANSWER),
                      UserAction(TimeRange(t3), aid, 'u5', UPVOTE_ANSWER))

    assert sa.cand_edges[11] == \
           FollowEdge(UserAction(TimeRange(t2, t3), aid, 'u3', UPVOTE_ANSWER),
                      UserAction(t2, aid, 'u2', UPVOTE_ANSWER|COMMENT_ANSWER|COLLECT_ANSWER))

    assert sa.cand_edges[12] == \
           FollowEdge(UserAction(TimeRange(t2, t3), aid, 'u3', UPVOTE_ANSWER),
                      UserAction(t5, aid, 'u7', COMMENT_ANSWER))

    assert sa.cand_edges[13] == \
        FollowEdge(UserAction(t3, aid, 'u4', UPVOTE_ANSWER|COLLECT_ANSWER),
                   UserAction(TimeRange(t3), aid, 'u5', UPVOTE_ANSWER))

    assert sa.cand_edges[14] == \
           FollowEdge(UserAction(t3, aid, 'u4', UPVOTE_ANSWER|COLLECT_ANSWER),
                      UserAction(t2, aid, 'u2', UPVOTE_ANSWER|COMMENT_ANSWER|COLLECT_ANSWER))

    assert sa.cand_edges[15] == \
           FollowEdge(UserAction(t3, aid, 'u4', UPVOTE_ANSWER|COLLECT_ANSWER),
                      UserAction(t5, aid, 'u7', COMMENT_ANSWER))

    assert sa.cand_edges[16] == \
        FollowEdge(UserAction(TimeRange(t3), aid, 'u5', UPVOTE_ANSWER),
                   UserAction(t2, aid, 'u2', UPVOTE_ANSWER|COMMENT_ANSWER|COLLECT_ANSWER))

    assert sa.cand_edges[17] == \
           FollowEdge(UserAction(TimeRange(t3), aid, 'u5', UPVOTE_ANSWER),
                      UserAction(t5, aid, 'u7', COMMENT_ANSWER))

    assert sa.cand_edges[18] == \
           FollowEdge(UserAction(TimeRange(t3), aid, 'u5', UPVOTE_ANSWER),
                      UserAction(t3, aid, 'u4', UPVOTE_ANSWER|COLLECT_ANSWER))

    pprint(sa.gen_features())