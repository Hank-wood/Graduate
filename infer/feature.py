"""
生成推断 follow 关系需要的 feature
有两种输入
1. infer.py 生成的 analysis.dynamic 中的已标注数据, 形如
{
    'time':
    'aid':
    'id':
    'children': [
        {},
        {
            children: []
        }
    ],
    links: []
}

2. 抓取的静态的问题和回答

我们需要对两种输入分别处理, 先转化成统一的形式(内存中), 然后生成 feature

推断 follow 时不应该涉及跨答案特征, 因为follow特征永远是优先选择的。
这个统一形式应该只包含能从静态问答中获取的信息。
问题的所有信息删除 question follower 时间
comment 四元组
collect 四元组
answer 四元组删除，time = None

提取的 feature 只是为了推断 follow，用不到 question 和其它 answer 的信息
"""

from itertools import chain
from typing import Union
from datetime import datetime

from icommon import *
from iutils import *
from user import UserManager
from client_pool2 import get_client


class TimeRange:
    def __init__(self, start=None, end=None):
        self.start = start
        self.end = end

    def __sub__(self, other: datetime):
        """
        :param other: comment or collect 时间, upvote已经用相对顺序判定
        :return: 1, -1, 0
        """
        if self.start is not None and self.start > other:
            return 1  # self > other
        elif self.end is not None and self.end < other:
            return -1  # self < other
        else:
            return 0  # unknown


class StaticAnswer:
    """
    表示一个静态答案
    """

    def __init__(self, tid, aid):
        self.tid = tid
        self.aid = aid
        self.upvoters = []
        self.commenters = []
        self.collectors = []
        self.cand_edges = []  # 候选边
        self.affecters = None
        self.root = None
        self.answer_time = None

    def load_from_dynamic(self):
        """
        从 zhihu_data 加载 answer 信息
        """
        # TODO: db 从外部加载
        answer_doc = db[a_col(self.tid)].find_one({'aid': self.aid})
        assert answer_doc is not None
        self.root = UserAction(answer_doc['time'], self.aid, answer_doc['answerer'],
                               ANSWER_QUESTION)
        self.answer_time = answer_doc['time']

        # 和 dynamic 不同, upvote time 设置成 None
        self.upvote_ids = [u['uid'] for u in answer_doc['upvoters']]
        self.upvoters = [
            UserAction(u['time'], self.aid, u['uid'], UPVOTE_ANSWER)
            # UserAction(None, self.aid, u['uid'], UPVOTE_ANSWER)
            for u in answer_doc['upvoters']
        ]
        self.commenters = [
            UserAction(u['time'], self.aid, u['uid'], COMMENT_ANSWER)
            for u in answer_doc['commenters']
        ]
        self.collectors = [
            UserAction(u['time'], self.aid, u['uid'], COLLECT_ANSWER)
            for u in answer_doc['collectors']
        ]
        # 插值. comment 肯定有时间信息, 不处理
        interpolate(self.collectors)
        self.affecters = list(chain(
            [self.root], self.upvoters, self.commenters, self.collectors))

    def load_from_static(self):
        """
        从抓取的静态答案数据库加载 answer
        """
        pass

    def gen_edges(self):
        """
        生成候选边
        顺序, answerer -> up1 -> up2 -> ... -> upn, 分别作为候选边的起点
        候选边终点分别是 [up1,up2,...up_n,comm1,...,comm_n,coll1,...,coll_n]
        """
        # TODO: 融合 uid 相同的点
        # 1. 多个tail uid 相同,type 不同,直接 |
        # 2. 把uid 相同的 commenters 和 collectors 合并到 upvoters 里面
        # 3. 能添加 TimeRange 的添加 TimeRange
        for i, head in enumerate(self.affecters[:len(self.upvoters) + 1]):
            for tail in self.affecters[i+1:]:
                if self.has_follow_relation(head, tail):
                    self.cand_edges.append(FollowEdge(head, tail))

    def gen_features(self):
        """
        生成 features
        :return: n_samples * n_features vector
        """
        return [
            [self.feature_head_rank(edge),
             *self.feature_node_type(edge),
             self.feature_relative_order(edge)] for edge in self.cand_edges
        ]

    def feature_head_rank(self, edge: FollowEdge) -> int:
        """
        head 在 tail 的候选中排第几
        """
        rank = 0
        head, tail = edge.head, edge.tail
        for cand in self.cand_edges:
            if cand.tail is tail:
                if cand.head is head:
                    return rank
                else:
                    rank += 1

    def feature_node_type(self, edge: FollowEdge) -> list:
        """
        因为head不是 answer 就是upvote,所以其实特征只需要提供 is_answer
        :return:
        [head_is_answer, tail_is_upvote, tail_is_comment, tail_is_collect]
        """
        head, tail = edge.head, edge.tail
        return [
            is_answer(head),
            is_upvote(tail),
            is_comment(tail),
            is_collect(tail)
        ]

    def feature_relative_order(self, edge: FollowEdge) -> int:
        """
        判断 edge.head, edge.tail 相对顺序
        head 只可能 answer or upvote
        time 可能是 None, datetime, TimeRange(start, end)
        :return:
            -1 if head.time < tail.time;
            1 if head.time >= tail.time;
            0 if unknown
        """
        head, tail = edge.head, edge.tail

        if is_answer(head):
            return -1

        # 当且仅当 head 是 upvote 时 tail 才可能是 upvote
        if is_upvote(tail):
            if self.upvote_ids.index(head.uid) < self.upvote_ids.index(tail.uid):
                return -1
            else:
                return 1

        # 现在 tail.time 只能是 datetime 了, 因为 tail 必然是 comment or collect
        if head.time is None:
            return 0

        # head.time is TimeRange
        return head.time - tail.time

    def gen_samples(self):
        """
        只有当用来从 dynamic 数据训练时才使用此方法
        :return: 0, 1 序列表示某关注关系是否是 follow relation
        """
        samples = []
        tree_data = db2.dynamic.find_one({'aid': self.aid}, {'_id': 0})
        links = {
            (l['source'], l['target']) for l in tree_data['links']
            if l['reltype']==RelationType.follow
        }
        for cand in self.cand_edges:
            if (cand.head.uid, cand.tail.uid) in links:
                samples.append(1)
            else:
                samples.append(0)

        return samples

    @staticmethod
    def has_follow_relation(head: UserAction, tail: UserAction):
        """
        determine if tail user follows head user
        时间以 tail 的时间为准, 因为在传播发生在 tail.time
        这里牺牲了性能因为每次都要扫 list,没有像 component 里使用set
        :return: bool
        """
        action_time = tail.time
        followers = user_manager.get_user_follower(head.uid, action_time)
        followees = user_manager.get_user_followee(tail.uid, action_time)
        if followers is not None:
            return True if tail.uid in followers else False
        elif followees is not None:
            return True if head.uid in followees else False
        else:
            u1 = get_client().author(USER_PREFIX + tail.uid)
            u2 = get_client().author(USER_PREFIX + head.uid)
            if u1.followee_num < u2.follower_num:
                followees = user_manager.fetch_user_followee(u1)
                return True if head.uid in followees else False
            else:
                followers = user_manager.fetch_user_follower(u2)
                return True if tail.uid in followers else False


class StaticQuestionWithAnswer:
    """
    表示一个静态问题和它的所有答案, 用于启发式推断 qlink, noti, recomm
    """
    def __init__(self):
        pass


if __name__ == '__main__':
    import pymongo
    from pprint import pprint
    db = pymongo.MongoClient('127.0.0.1', 27017).get_database('sg1')
    sys.modules[__name__].__dict__['db'] = db
    sys.modules[__name__].__dict__['user_manager'] = UserManager(db.user)
    sa = StaticAnswer(tid='19553298', aid="87423946")
    sa.load_from_dynamic()
    sa.gen_edges()
    pprint(sa.cand_edges)
    pprint(sa.gen_samples())

    with open('upvoters_87423946', 'w') as f:
        adoc = db.get_collection('19553298_a').find_one({'aid': "87423946"})
        for upvoter in adoc['upvoters']:
            f.write("%s %s\n" % (upvoter['uid'], str(upvoter['time'])))

    with open('upvoters_87424209', 'w') as f:
        adoc = db.get_collection('19550517_a').find_one({'aid': "87424209"})
        for upvoter in adoc['upvoters']:
            f.write("%s %s\n" % (upvoter['uid'], str(upvoter['time'])))
