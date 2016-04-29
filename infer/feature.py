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

import json
from itertools import chain
from typing import Union
from copy import copy
from collections import defaultdict
from operator import itemgetter
import pickle
from pprint import pprint

import networkx
from networkx.readwrite import json_graph

from icommon import *
from iutils import *
from user import UserManager
from client_pool2 import get_client


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
        self.root = None
        self.answer_time = None
        self.merged_action_table = {}  # UserAction Merge result, {uid: UserAction}

    def load_from_raw(self, coll_name=None):
        """
        从 zhihu_data 加载 answer 信息
        """
        if not coll_name:
            a_coll = db[a_col(self.tid)]
        else:
            a_coll = db[coll_name]
        answer_doc = a_coll.find_one({'aid': self.aid})
        assert answer_doc is not None
        self.root = UserAction(answer_doc['time'], self.aid,
                               answer_doc['answerer'], ANSWER_QUESTION)
        self.answer_time = answer_doc['time']

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
            [self.root], self.upvoters, self.commenters, self.collectors))

    def load_from_dynamic(self):
        """
        从推断出的动态传播图加载 answer
        """
        # tree_data = db2.dynamic.find_one({'aid': self.aid}, {'_id': 0})
        return transform_outgoing(
            db2.dynamic_sg1.find_one({'aid': self.aid}, {'_id': 0}))

    def load_from_static(self):
        """
        从推断出的静态传播图加载 answer
        """
        # tree_data = db2.dynamic.find_one({'aid': self.aid}, {'_id': 0})
        return transform_outgoing(
            db2.static_sg1.find_one({'aid': self.aid}, {'_id': 0}))

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
        if self.root.uid == '':  # 排除匿名回答者
            start = 1
        for i, head in enumerate(self.affecters[start:len(self.upvoters) + 1]):
            for tail in self.affecters[i+1:]:
                # answerer 不作为 tail, 因为他能自动接收消息, 不需要推断
                if head.uid == tail.uid or tail.uid == self.root.uid:
                    continue
                if self.has_follow_relation(head, tail):
                    realhead = hashtable[head.uid]
                    realtail = hashtable[tail.uid]
                    edge = FollowEdge(realhead, realtail)
                    reverse_edge = FollowEdge(realtail, realhead)
                    if edge not in edge_set and reverse_edge not in edge_set:
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

    def gen_features_without_isanswer(self):
        """
        :return: 除 is_answer 之外的 feature
        """
        return [
            [self._feature_head_rank(edge),
             *self._feature_node_type(edge)[1:],
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
    def _feature_node_type(edge: FollowEdge) -> list:
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
        target = []
        tree_data = self.load_from_dynamic()
        links = {
            (l['source'], l['target']) for l in tree_data['links']
            if l['reltype'] == RelationType.follow
        }
        for cand in self.cand_follow_edges:
            if (cand.head.uid, cand.tail.uid) in links:
                target.append(1)
            else:
                target.append(0)

        return target

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
        # use merged action too
        propagators = [self.merged_action_table[upvote.uid] for upvote in self.upvoters]
        propagators.insert(0, self.root)
        self.sqa.add_answer_propagator(propagators)

    def evaluate_follow(self):
        """推断follow关系,用于评价follow关系推断的效果. 只有有follow关系边的才能调用
        :return: result, target
        """
        if not self.cand_follow_edges:
            return [], []
        target = self.gen_target()
        result = []
        tree_data = self.load_from_static()
        links = {
            (l['source'], l['target']) for l in tree_data['links']
            if l['reltype']==RelationType.follow
        }
        for cand in self.cand_follow_edges:
            if (cand.head.uid, cand.tail.uid) in links:
                result.append(1)
            else:
                result.append(0)

        return result, target

    def evaluate_all(self):
        dynamic_tree = self.load_from_dynamic()
        dynamic_links = {
            (l['source'], l['target']): l['reltype']
            for l in dynamic_tree['links']
        }
        answerer = dynamic_tree['id']
        dynamic_graph = json_graph.tree_graph(dynamic_tree)
        static_tree = self.load_from_static()
        static_links = {
            (l['source'], l['target']): l['reltype']
            for l in static_tree['links']
        }
        static_graph = json_graph.tree_graph(static_tree)
        if dynamic_graph.number_of_nodes() != static_graph.number_of_nodes():
            for node in dynamic_graph.nodes():
                if not static_graph.has_node(node):
                    print("static graph lack node " + node + ' ' + self.aid)
            for node in static_graph.nodes():
                if not dynamic_graph.has_node(node):
                    print("dynamic graph lack node " + node + ' ' + self.aid)

        target_edges = []
        result_edges = []
        for node in dynamic_graph.nodes():
            if node == answerer:
                continue
            assert len(dynamic_graph.in_edges(node)) == 1
            assert len(static_graph.in_edges(node)) == 1
            dynamic_edge = dynamic_graph.in_edges(node)[0]
            dynamic_edge += (dynamic_links[dynamic_edge],)
            target_edges.append(dynamic_edge)  # set reltype
            static_edge = static_graph.in_edges(node)[0]
            static_edge += (static_links[static_edge],)
            result_edges.append(static_edge)

        return result_edges, target_edges

    def evaluate_graph_sim(self):
        dynamic_graph = json_graph.tree_graph(self.load_from_dynamic())
        static_graph = json_graph.tree_graph(self.load_from_static())
        return static_graph, dynamic_graph

    def infer(self, model, save_to_db=False, coll_name=None):
        """
        :param coll_name: 写入的 collection name
        推断静态传播图
        """
        # 用训练好的模型标注 follow 边, 把 follow 边加入图中
        if self.cand_follow_edges:
            features = self.gen_features_without_isanswer()
            result = model.predict(features)
            probs = model.predict_proba(features)
            for value, prob, edge in zip(result, probs, self.cand_follow_edges):
                head, tail = edge.head, edge.tail
                if value:
                    # 添加标注为 follow 关系的 edge 的 head, tail
                    if not self.graph.has_node(head.uid):
                        self.add_node(head)
                    if not self.graph.has_node(tail.uid):
                        self.add_node(tail)
                    self.add_edge(head, tail, RelationType.follow, prob=prob)

            # 对同一个接收者的多条边, 选择 prob 最高的
            for node in self.graph.nodes():
                if self.graph.in_degree(node) > 1:
                    edges = self.graph.in_edges(node, data=True)
                    max_prob = max([edge[2]['prob'][1] for edge in edges])
                    for edge in edges:
                        if edge[2]['prob'][1] < max_prob:
                            # print("delete edge: " + str(edge))
                            self.graph.remove_edge(edge[0], edge[1])
                assert self.graph.in_degree(node) <= 1

        # 筛选出不存在于图中 or in-degree=0 的点
        for uid, merged_action in self.merged_action_table.items():
            if uid == self.root.uid:
                continue    # skip answerer
            if self.graph.has_node(uid) and self.graph.in_degree(uid) > 0:
                continue
            relation = self._infer_node(merged_action)
            self.add_node(relation.tail)
            self.add_edge(*relation)

        for node in self.graph.nodes():
            self.graph.node[node]['acttype'] = acttype2str(self.graph.node[node]['acttype'])
            """
            path = [node]
            while node != self.root.uid:
                parent = self.graph.predecessors(node)
                if parent:
                    node = parent[0]
                    path.insert(0, node)
                else:
                    print(path)
                    break
            else:
                print(path)
            """

        # tree
        assert self.graph.number_of_nodes() == self.graph.number_of_edges() + 1

        tree_data = json_graph.tree_data(self.graph, root=self.root.uid)
        node_links = json_graph.node_link_data(self.graph)
        links = [
            {
                'source': node_links['nodes'][link['source']]['id'],
                'target': node_links['nodes'][link['target']]['id'],
                'reltype': link['reltype']
            }
            for link in node_links['links']
            ]
        tree_data['links'] = links
        tree_data['tid'] = self.tid

        if save_to_db:
            db2.get_collection(coll_name).replace_one({'aid': self.aid},
                                            transform_incoming(tree_data),
                                            upsert=True)
        else:
            with open('data/%s.json' % self.aid, 'w') as f:
                json.dump(tree_data, f, cls=MyEncoder, indent='\t')

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
        action_time_is_datetime = isinstance(action_time, datetime)
        action_time_is_timerange = isinstance(action_time, TimeRange)

        # noti
        if uid in self.sqa.question_follower_dict:
            follow_time = self.sqa.question_follower_dict[action.uid].time
            # answer_time 一定是 datetime
            if follow_time <= self.answer_time:
                # 这里认为只要 follow_time 不确定晚于答案时间, 就是 noti
                return Relation(self.root, action, RelationType.notification)

        # qlink
        # 同 uid 在其它答案中出现, 且时间有可能早于当前操作, 就认为是 qlink
        for cand in self.sqa.user_actions[uid]:
            if cand.aid == self.aid:
                continue
            cand_time_is_datetime = isinstance(cand.time, datetime)
            cand_time_is_timerange = isinstance(cand.time, TimeRange)

            if cand_time_is_datetime and action_time_is_datetime and cand.time < action_time:
                return Relation(self.root, action, RelationType.qlink)
            elif cand_time_is_timerange and cand.time <= action_time:
                return Relation(self.root, action, RelationType.qlink)
            elif action_time_is_timerange and action_time <= cand.time:
                return Relation(self.root, action, RelationType.qlink)

        # 用关注关系判断 qlink
        for cand in self.sqa.propagators:
            if cand.uid == '' or cand.aid == self.aid:  # 同aid不能算qlink
                continue
            # 判断时间关系, 如果 cand 确定大, 则排除
            cand_time_is_datetime = isinstance(cand.time, datetime)
            cand_time_is_timerange = isinstance(cand.time, TimeRange)
            if cand_time_is_datetime and action_time_is_datetime and cand.time >= action_time:
                continue
            elif cand_time_is_timerange and cand.time - action_time > 0:
                continue
            elif action_time_is_timerange and action_time - cand.time < 0:
                continue

            # 逻辑和推断follow完全一样,为了不重复生成followees,不单独写成函数
            followers = user_manager.get_user_follower(cand.uid, action.time)
            if followees is not None:
                if cand.uid in followees:
                    # cand is action.uid's followee
                    return Relation(self.root, action, RelationType.qlink)
            elif followers is not None:
                if action.uid in followers:
                    # action.uid is cand's follower
                    return Relation(self.root, action, RelationType.qlink)
            else:
                logger.warning("%s lacks follower,%s lacks followee" %
                               (cand.uid, action.uid))
                u1 = get_client().author(USER_PREFIX + action.uid)
                u2 = get_client().author(USER_PREFIX + cand.uid)
                if u1.followee_num < u2.follower_num:
                    followees = user_manager.fetch_user_followee(u1)
                    if cand.uid in followees:
                        # cand is action.uid's followee
                        return Relation(self.root, action, RelationType.qlink)
                else:
                    followers = user_manager.fetch_user_follower(u2)
                    if action.uid in followers:
                        # action.uid is cand's follower
                        return Relation(self.root, action, RelationType.qlink)

        # 之前都不是, 只能是 recommendation 了
        return Relation(self.root, action, RelationType.recommendation)

    def add_node(self, useraction: UserAction):
        self.graph.add_node(useraction.uid,
                            aid=useraction.aid,
                            acttype=useraction.acttype,
                            time=useraction.time)

    def add_edge(self, useraction1, useraction2, reltype, prob=None):
        """
        :param useraction1:
        :param useraction2:
        :param reltype:
        :param prob: predict_proba value
        :return:
        """
        self.graph.add_edge(useraction1.uid, useraction2.uid, reltype=reltype,
                            prob=prob)

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


class StaticQuestionWithAnswer:
    """
    表示一个静态问题和它的所有答案, 用于启发式推断 qlink, noti, recomm
    一定记得在调用 StaticAnswer.infer 之前调用所有 StaticAnswer 的 infer_preparation
    和 fill_question_follower_time
    """
    def __init__(self, tid, qid, coll_name=None):
        self.tid = tid
        self.qid = qid
        self.user_actions = defaultdict(list)  # 记录所有 user action for qlink match
        self.question_followers = []  # [UserAction]
        self.question_follower_dict = {}  # {uid->UserAction}
        self.propagators = []   # 和 dynamic 不同,这里直接用list,不排序
        self.coll_name = coll_name
        self.load_question_followers()

    def add_user_actions(self, user_actions: dict):
        for uid, merged_action in user_actions.items():
            # 不按时间排序, 因为存在 None, TimeRange 等无法排序的时间
            # 提问者和 question followers 是不在 user_actions 里的
            self.user_actions[uid].append(merged_action)

    def add_answer_propagator(self, propagators):
        self.propagators.extend(propagators)

    def fill_question_follower_time(self):
        """
        在所有答案的 infer_preparation 调用完之后调用
        填充 question follower 时间信息. 算法如下
        生成一个序列
        [t1, t2, t3, ...]
        每个元素是 user_action[uid][0].time, 即第一次出现的时间
        在这个序列上跑 Longest Increasing Subsequence 算法
        """
        time_list = []
        index_of_followers = []

        start = 1 if self.question_followers[0].acttype == ASK_QUESTION else 0
        # 不包含提问者, 防止提问者被他的其它操作的时间污染
        for i in range(start, len(self.question_followers)):
            uid = self.question_followers[i].uid
            if uid in self.user_actions:
                action_list = self.user_actions[uid]
                t = timerange2datetime(action_list[0].time)
                if t:
                    index_of_followers.append(i)
                    time_list.append(t)

        # 填充在 LIS 中的时间
        for time, index in zip(*longestIncreasingSubsequence(time_list)):
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
        if not self.coll_name:
            q_coll = db[q_col(self.tid)]
        else:
            q_coll = db[self.coll_name]
        q_doc = q_coll.find_one({'qid': self.qid})
        assert q_doc is not None
        assert self.question_followers == []
        asker = q_doc['asker']
        self.question_followers.append(
            UserAction(q_doc['time'], '', asker, ASK_QUESTION)
        )
        # follower 是从老到新, 顺序遍历可保证 question_followers 从老到新
        for f in q_doc['follower']:
            if f['uid'] != asker:
                follow_action = UserAction(None, '', f['uid'], FOLLOW_QUESTION)
                self.question_followers.append(follow_action)

        for follower in self.question_followers:
            self.question_follower_dict[follower.uid] = follower
        self.propagators.extend(self.question_followers)


class FeatureContainer:
    """
    feature 的容器, 可以选择性地返回 feature, 用 pickle 存储
    每次添加新 feature 都重新计算 feature container
    需要保证 feature_types 的特征顺序和 gen_features 返回的顺序一致
    """
    feature_types = ('h_rank','is_answer','is_upvote','is_comment',
                     'is_collect', 'r_order')

    def __init__(self, ):
        self.features = []  # [[f11, f12], [f21, f22], ...]
        self.target = []  # [1, 0, 0, 1, ...]

    def append(self, flist, target):
        """
        :param flist: [[f11, f12], [f21, f22], ...]
        """
        self.features.extend(flist)
        self.target.extend(target)

    def get_features(self, feature_names):
        choosen_index = [
            i for i, ftype in enumerate(self.feature_types) if ftype in feature_names
        ]
        return [itemgetter(*choosen_index)(f) for f in self.features]

    def dump(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump({
                'feature': self.features,
                'target': self.target
            }, f)

    def load(self, filename):
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                data = pickle.load(f)
                self.features = data['feature']
                self.target = data['target']


if __name__ == '__main__':
    import pymongo
    from pprint import pprint
    db = pymongo.MongoClient('127.0.0.1', 27017).get_database('sg1')
    sys.modules[__name__].__dict__['db'] = db
    sys.modules[__name__].__dict__['user_manager'] = UserManager(db.user)
    sa = StaticAnswer(tid='19553298', aid="87423946")
    sa.load_from_raw()
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
