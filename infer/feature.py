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
from copy import copy

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
        因此不会发生两个 TimeRange 相减的情况
        :return: 1, -1, 0
        """
        if self.start is not None and self.start > other:
            return 1  # self > other
        elif self.end is not None and self.end < other:
            return -1  # self < other
        else:
            return 0  # unknown

    def __eq__(self, other):
        return self.start == other.start and self.end == other.end

    def __str__(self):
        return str(self.__dict__)


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
        self.cand_follow_edges = []  # 候选边
        self.affecters = None
        self.answerer = None
        self.answer_time = None
        self.hashtable = {}  # UserAction Merge result, {uid: UserAction}

    def load_from_dynamic(self):
        """
        从 zhihu_data 加载 answer 信息
        """
        # TODO: db 从外部加载
        answer_doc = db[a_col(self.tid)].find_one({'aid': self.aid})
        assert answer_doc is not None
        self.answerer = UserAction(answer_doc['time'], self.aid,
                                   answer_doc['answerer'], ANSWER_QUESTION)
        self.answer_time = answer_doc['time']
        self.root = UserAction(answer_doc['time'], self.aid, uid, ANSWER_QUESTION)

        # 和 dynamic 不同, upvote time 设置成 None
        self.upvote_ids = [u['uid'] for u in answer_doc['upvoters']]
        self.upvoters = [
            UserAction(TimeRange(), self.aid, u['uid'], UPVOTE_ANSWER)
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
            [self.answerer], self.upvoters, self.commenters, self.collectors))

    def load_from_static(self):
        """
        从抓取的静态答案数据库加载 answer
        """
        pass

    def build_cand_edges(self):
        """
        生成候选边
        顺序, answerer -> up1 -> up2 -> ... -> upn, 分别作为候选边的起点
        候选边终点分别是 [up1,up2,...up_n,comm1,...,comm_n,coll1,...,coll_n]
        # 融合 uid 相同的点
        # 1. 多个tail uid 相同,type 不同,直接 |
        # 2. 把uid 相同的 commenters 和 collectors 合并到 upvoters 里面
        # 3. 能添加 TimeRange 的添加 TimeRange
         注意这造成了一个情况: cand_edges 中的 UserAction在upvoters/commenters/
         collectors 中不存在
        """

        # step 1, build hashtable, values are useractions used in cand_edges
        hashtable = self.hashtable  # record uid -> UserAction
        for useraction in self.affecters:
            uid = useraction.uid
            if uid not in hashtable:
                hashtable[uid] = copy(useraction)
            else:
                hashtable[uid].acttype |= useraction.acttype
                # 评论/收藏者点赞,把评论/收藏时间认为是点赞时间
                if isinstance(hashtable[uid].time, TimeRange):
                    hashtable[uid].time = useraction.time
                else:
                    hashtable[uid].time = min(hashtable[uid].time,
                                              useraction.time)

        # step 3, set upvote's TimeRange's start and end if possible
        # 这里修改的都是 hashtable 里的 UserAction, 保持 up/cm/cl 不变
        # set start
        i = 1  # 0 is answer
        while i < len(self.upvote_ids) + 1:
            time = hashtable[self.affecters[i].uid].time
            if isinstance(time, datetime):
                i += 1
                while not isinstance(hashtable[self.affecters[i].uid].time, datetime):
                    hashtable[self.affecters[i].uid].time.start = time
                    i += 1
            else:
                i += 1

        # set end
        i = len(self.upvote_ids)
        while i > 0:
            time = hashtable[self.affecters[i].uid].time
            if isinstance(time, datetime):
                i -= 1
                while not isinstance(hashtable[self.affecters[i].uid].time, datetime):
                    hashtable[self.affecters[i].uid].time.end = time
                    i -= 1
            else:
                i -= 1

        # step 2, append distinct edges into cand_edges
        edge_set = set()
        start = 0
        if self.answerer.uid == '':  # 排除匿名回答者
            start = 1
        for i, head in enumerate(self.affecters[start:len(self.upvoters) + 1]):
            for tail in self.affecters[i+1:]:
                # answerer 不作为 tail, 因为他能自动接收消息, 不需要推断
                if head.uid == tail.uid or tail.uid == self.answerer.uid:
                    continue
                if self.has_follow_relation(head, tail):
                    realhead = hashtable[head.uid]
                    realtail = hashtable[tail.uid]
                    edge = FollowEdge(realhead, realtail)
                    if edge not in edge_set:
                        self.cand_follow_edges.append(edge)
                        edge_set.add(edge)

    def gen_features(self) -> list:
        """
        生成 features
        :return: n_samples * n_features vector
        """
        return [
            [self.feature_head_rank(edge),
             *self.feature_node_type(edge),
             self.feature_relative_order(edge)] for edge in self.cand_follow_edges
        ]

    def feature_head_rank(self, edge: FollowEdge) -> int:
        """
        head 在 tail 的候选中排第几
        """
        rank = 0
        head, tail = edge.head, edge.tail
        for cand in self.cand_follow_edges:
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
        if isinstance(head.time, datetime):
            return -1 if head.time < tail.time else 1
        else:
            return head.time - tail.time  # see TimeRange.__sub__

    def gen_target(self) -> list:
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
        for cand in self.cand_follow_edges:
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
            print("%s lacks follower,%s lacks followee" % (head.uid, tail.uid))
            u1 = get_client().author(USER_PREFIX + tail.uid)
            u2 = get_client().author(USER_PREFIX + head.uid)
            if u1.followee_num < u2.follower_num:
                followees = user_manager.fetch_user_followee(u1)
                return True if head.uid in followees else False
            else:
                followers = user_manager.fetch_user_follower(u2)
                return True if tail.uid in followers else False

    def infer_preparation(self, sqa):
        """
        :param sqa: StaticQuestionWithAnswer object
        infer 的准备工作, 填充 StaticQuestionWithAnswer 数据
        """
        self.sqa = sqa
        self.graph = networkx.DiGraph()
        self.add_node(self.root)

        # fill user_actions
        all_user_actions = [self.root] + self.upvoters + self.commenters + self.collectors
        key = lambda x: x.uid
        all_user_actions.sort(key=key)
        user_actions = {}
        for key, group in groupby(all_user_actions, key=key):
            if key != '':  # 排除匿名
                user_actions[key] = list(group)
        self.sqa.add_user_actions(user_actions)

    def infer(self, model):
        """
        推断静态传播图
        :return:
        """
        self.add_follow_edges(model)
        # 筛选出不存在于图中 or in-degree=0 的点
        for uid, merged_action in self.hashtable.items():
            if self.graph.has_node(uid) and self.graph.in_degree(uid) > 0:
                continue
            self._infer_node(merged_action)

    def add_follow_edges(self, model):
        """
        用训练好的模型标注 follow 边, 把 follow 边加入图中
        :param model: 训练好的模型
        :return:
        """
        result = clf.predict(self.cand_follow_edges)
        for value, edge in zip(result, self.cand_follow_edges):
            head, tail = edge.head, edge.tail
            if value:
                # 添加标注为 follow 关系的 edge 的 head, tail
                if not self.graph.has_node(head.uid):
                    self.graph.add_node(head)
                if not self.graph.has_node(tail.uid):
                    self.graph.add_node(tail)
                self.graph.add_edge(head, tail, RelationType.follow)

    def _infer_node(self, action):
        """
        infer noti, qlink, recommendation relation
        """

        # noti
        # qlink 如果不是 follow&noti, 且有在其它答案中出现, 那么就认为是 qlink



    def add_node(self, useraction: UserAction):
        self.graph.add_node(useraction.uid,
                            aid=useraction.aid,
                            acttype=useraction.acttype,
                            time=useraction.time)

    def add_edge(self, useraction1, useraction2, reltype):
        self.graph.add_edge(useraction1.uid, useraction2.uid, reltype=reltype)


class StaticQuestionWithAnswer:
    """
    表示一个静态问题和它的所有答案, 用于启发式推断 qlink, noti, recomm
    一定记得在调用 StaticAnswer.infer 之前调用所有 StaticAnswer 的 infer_preparation
    和 fill_question_follower_time
    """
    def __init__(self):
        self.user_actions = {}  # 记录所有 user action for qlink match
        self.question_followers = []  # [UserAction]
        self.load_question_followers()

    def add_user_actions(self, user_actions: dict):
        for key, value in user_actions.items():
            self.user_actions[key] = self.user_actions.get(key, []) + value
            self.user_actions[key].sort(key=lambda x: x.time)

    def fill_question_follower_time(self):
        """
        在所有答案的 infer_preparation 调用完之后调用
        填充 question follower 时间信息. 算法如下
        生成一个序列
        [t1, t2, t3, ...]
        每个元素是
        1) 唯一的 follower.time
        2) (user_action[uid][0].time + user_action[uid][-1].time) / 2
        在这个序列上跑 Longest Increasing Subsequence 算法
        check 生成的 LIS, 如果一个 meantime 没有被选中, 则看它的时间段和左右两边有无重合
        如果有重合, 则把这个重合时间段的中点作为时间
        """
        time_list = []
        index_of_followers = []

        for i, follower in enumerate(self.question_followers):
            uid = follower.uid
            if uid in self.user_actions:
                action_list = self.user_actions[uid]
                index_in_followers.append(i)
                if len(action_list) == 1:
                    time_list.append(action_list[0].time)
                else:
                    time_list.append((action_list[0].time + action_list[-1].time)/2)

        time_picked, index_of_timelist = longestIncreasingSubsequence(time_list)
        # 填充在 LIS 中的时间
        for time, index in zip(time_picked, index_of_timelist):
            if index == 0:
                continue    # skip asker
            index_of_follower = index_of_followers[index]
            self.question_followers[index_of_follower].time = time

        # 填充 TimeRange.start
        left_time = self.question_followers[0].time
        for follower in self.question_followers:
            if follower.time:
                left_time = follower.time
                continue
            follower.time = TimeRange(start=left_time)

        # 填充 TimeRange.end
        right_time = None
        for follower in reversed(self.question_followers):
            if isinstance(follower.time, datetime):
                right_time = follower.time
                continue
            follower.time.end = right_time

    def load_question_followers(self):
        """
        load question followers from database. 同时加入 propagators
        """
        q_doc = db[q_col(self.tid)].find_one({'qid': self.qid})
        assert q_doc is not None
        self.question_followers.append(
            UserAction(q_doc['time'], '', q_doc['asker'], ASK_QUESTION)
        )
        # follower 是从老到新, 顺序遍历可保证 question_followers 从老到新
        for f in q_doc['follower']:
            follow_action = UserAction(None, '', f['uid'], FOLLOW_QUESTION)
            self.question_followers.append(follow_action)

        # list(map(self.propagators.put, self.question_followers))

if __name__ == '__main__':
    import pymongo
    from pprint import pprint
    db = pymongo.MongoClient('127.0.0.1', 27017).get_database('sg1')
    sys.modules[__name__].__dict__['db'] = db
    sys.modules[__name__].__dict__['user_manager'] = UserManager(db.user)
    sa = StaticAnswer(tid='19553298', aid="87423946")
    sa.load_from_dynamic()
    sa.build_cand_edges()
    pprint(sa.cand_follow_edges)
    pprint(sa.gen_target())

    with open('data/upvoters_87423946', 'w') as f:
        adoc = db.get_collection('19553298_a').find_one({'aid': "87423946"})
        for upvoter in adoc['upvoters']:
            f.write("%s %s\n" % (upvoter['uid'], str(upvoter['time'])))

    with open('data/upvoters_87424209', 'w') as f:
        adoc = db.get_collection('19550517_a').find_one({'aid': "87424209"})
        for upvoter in adoc['upvoters']:
            f.write("%s %s\n" % (upvoter['uid'], str(upvoter['time'])))
