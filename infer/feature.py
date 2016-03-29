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
from collections import defaultdict

from icommon import *
from iutils import *
from user import UserManager
from client_pool2 import get_client


class TimeRange:
    def __init__(self, start=None, end=None):
        self.start = start
        self.end = end

    def __sub__(self, other: Union[datetime, TimeRange]):
        """
        用来判断时间相对顺序
        :return:
            -1 if self <= other;
            1 if self >= other;
            0 if unknown
        """
        if isinstance(other, datetime):
            if self.start and self.start >= other:
                return 1  # self > other
            elif self.end and self.end <= other:
                return -1  # self < other
            else:
                return 0  # unknown
        else:
            # TimeRange
            if self.end and other.start and self.end <= other.start:
                return -1
            elif self.start and other.end and self.start >= other.end:
                return 1
            else:
                return 0

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
        self.merged_action_table = {}  # UserAction Merge result, {uid: UserAction}

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
        hashtable = self.merged_action_table  # record uid -> UserAction
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
            [self._feature_head_rank(edge),
             *self._feature_node_type(edge),
             self._feature_relative_order(edge)] for edge in self.cand_follow_edges
            ]

    def _feature_head_rank(self, edge: FollowEdge) -> int:
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

    @staticmethod
    def _feature_node_type(self, edge: FollowEdge) -> list:
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

    def _feature_relative_order(self, edge: FollowEdge) -> int:
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
        self.build_cand_edges()
        # fill user_actions, 这里用 merged useraction
        self.sqa.add_user_actions(self.merged_action_table)

    def infer(self, model):
        """
        推断静态传播图
        """
        # 用训练好的模型标注 follow 边, 把 follow 边加入图中
        result = clf.predict(self.gen_features())
        for value, edge in zip(result, self.cand_follow_edges):
            head, tail = edge.head, edge.tail
            if value:
                # 添加标注为 follow 关系的 edge 的 head, tail
                if not self.graph.has_node(head.uid):
                    self.graph.add_node(head)
                if not self.graph.has_node(tail.uid):
                    self.graph.add_node(tail)
                self.graph.add_edge(head, tail, RelationType.follow)

        # 筛选出不存在于图中 or in-degree=0 的点
        for uid, merged_action in self.merged_action_table.items():
            if self.graph.has_node(uid) and self.graph.in_degree(uid) > 0:
                continue
            relation = self._infer_node(merged_action)
            self.add_node(relation.tail)
            self.add_edge(*relation)

    def _infer_node(self, action):
        """
        infer noti, qlink, recommendation relation
        """
        # user_manager 由外部加载
        from client_pool2 import get_client2 as get_client
        followees = user_manager.get_user_followee(action.uid, action.time)
        followees = set(followees) if followees is not None else None
        uid = action.uid
        action_time = action.time

        # noti
        if uid in self.sqa.question_follower_dict:
            follow_time = self.sqa.question_follower_dict[action.uid].time
            # follow_time 不是 datetime 就是 TimeRange
            if isinstance(follow_time, datetime) and follow_time <= self.answer_time:
                return Relation(self.root, action, RelationType.notification)
            elif follow_time - self.answer_time <= 0:
                # 这里认为只要 follow_time 不确定晚于答案时间, 就是 noti
                return Relation(self.root, action, RelationType.notification)

        # qlink
        # 同 uid 在其它答案中出现, 且时间有可能早于当前操作, 就认为是 qlink
        for cand in self.sqa.user_actions[uid]:
            if cand.aid == self.aid:
                continue
            cand_time_is_datetime = isinstance(cand.time, datetime)
            cand_time_is_timerange = isinstance(cand.time, TimeRange)
            action_time_is_datetime = isinstance(action_time, datetime)
            action_time_is_timerange = isinstance(action_time, TimeRange)

            if cand_time_is_datetime and action_time_is_datetime and cand.time < action_time:
                return Relation(self.root, action, RelationType.qlink)
            elif cand_time_is_timerange and cand.time - action_time <= 0:
                return Relation(self.root, action, RelationType.qlink)
            elif action_time_is_timerange and action_time - cand.time >= 0:
                return Relation(self.root, action, RelationType.qlink)



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
        self.user_actions = defaultdict(list)  # 记录所有 user action for qlink match
        self.question_followers = []  # [UserAction]
        self.question_follower_dict = {}  # {uid->UserAction}
        self.load_question_followers()

    def add_user_actions(self, user_actions: dict):
        for uid, merged_action in user_actions.items():
            # 不按时间排序, 因为存在 None, TimeRange 等无法排序的时间
            self.user_actions[key].append(merged_action)

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

        for follower in self.question_followers:
            self.question_follower_dict[follower.uid] = follower
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
