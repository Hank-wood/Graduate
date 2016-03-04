"""
定义推断所使用的

方法的设计一定要支持多进程, 因为推断要使用多进程加速
从数据库加载用 load
"""
import bisect
import logging
import json
from queue import PriorityQueue
from copy import copy
from typing import Union
from functools import reduce
from datetime import datetime

import networkx
from zhihu.author import ANONYMOUS
from networkx.readwrite import json_graph

from icommon import *
from iutils import *


logger = logging.getLogger(__name__)


class InfoStorage:
    """
    用来存储动态传播图推断所需的信息,包括答案affecters, 用户关注关系
    """
    def __init__(self, tid, qid):
        self.tid = tid
        self.qid = qid
        # 记录各个答案提供的能影响其它用户的用户, 推断qlink
        self.question_followers = []  # [UserAction]
        # self.answer_propagators = {}  # {aid: [UserAction]}, 暂时没用
        self.followers = {}  # user follower, {uid: []}
        self.followees = {}  # user followee, {uid: []}
        self.answers = {}  # {uid: UserAction(acttype=ANSWER_QUESTION)}
        self.propagators = PriorityQueue()
        self.load_question_followers()

    def load_question_followers(self):
        """
        load question followers from database. 同时加入 propagators
        """
        q_doc = db[q_col(self.tid)].find_one({'qid': self.qid})
        assert q_doc is not None
        self.question_followers.append(
             UserAction(q_doc['time'], None, q_doc['asker'], ASK_QUESTION)
        )
        # follower 是从老到新, 顺序遍历可保证 question_followers 从老到新
        for f in q_doc['follower']:
            follow_action = UserAction(f['time'], None, f['uid'], FOLLOW_QUESTION)
            self.question_followers.append(follow_action)

        interpolate(self.question_followers)
        list(map(self.propagators.put, self.question_followers))

    def add_answer_propagator(self, aid, propagators):
        """
        记录每个 answer 的 upvoter+answerer. 同时加入 propagators
        :param propagators: List of UserAction
        """
        answer_act = propagators[0]
        self.answers[answer_act.uid] = answer_act
        list(map(self.propagators.put, propagators))

    def get_user_follower(self, uid, time=None) -> Union[list, None]:
        """
        逻辑非常复杂
        if uid in self.followers, 返回 self.followers[uid]
        else
            if 数据库中有doc且有follower, 更新self.followers, 返回follower, 可为[]
            if 数据库中有doc但不包含follower, 返回None, self.followers[uid]=None
            if 数据库中没有doc, 返回None, self.followers[uid]=None
        time 指取到哪个时刻的follower
        """
        if uid in self.followers:
            if self.followers[uid] is None:
                return None
            else:
                return self.get_closest_users(self.followers[uid], time)

        user_doc = db['user'].find_one({'uid': uid}, {'follower': 1, '_id': 0})
        if user_doc is None:
            self.followers[uid] = None
            return None
        else:
            if 'follower' in user_doc:
                self.followers[uid] = user_doc['follower']
                return self.get_closest_users(user_doc['follower'], time)
            else:
                self.followers[uid] = None
                return None

    def fetch_user_follower(self, user) -> list:
        """
        之前没有follower, 要重新抓取, 返回抓到的, 并更新 self.followers
        """
        uids = [er.id for er in user.followers if er is not ANONYMOUS]
        db.user.update_one({
            'uid': user.id,
        }, {
            "$set": {
                "follower": [{
                    'time': datetime.now(),
                    'uids': uids
                }]
            }
        }, upsert=True)
        self.followers[user.id] = [{'time': datetime.now(), 'uids': uids}]
        return self.followers[user.uid]

    def get_user_followee(self, uid, time=None) -> Union[list, None]:
        """
        逻辑同 get_user_followee
        """
        if uid in self.followees:
            if self.followees[uid] is None:
                return None
            else:
                return self.get_closest_users(self.followees[uid], time)

        user_doc = db['user'].find_one({'uid': uid}, {'followee': 1, '_id': 0})
        if user_doc is None:
            self.followees[uid] = None
            return None
        else:
            if 'followee' in user_doc:
                self.followees[uid] = user_doc['followee']
                return self.get_closest_users(user_doc['followee'], time)
            else:
                self.followees[uid] = None
                return None

    def fetch_user_followee(self, user) -> list:
        uids = [ee.id for ee in user.followees if ee is not ANONYMOUS]
        db.user.update_one({
            'uid': user.id,
        }, {
            "$set": {
                "followee": [{
                    'time': datetime.now(),
                    'uids': uids
                }]
            }
        }, upsert=True)
        self.followees[user.id] = [{'time': datetime.now(), 'uids': uids}]
        return self.followees[user.id]

    @staticmethod
    def get_closest_users(flist, time) -> list:
        """
        调用此方法时, 数据库中已经确保有相应数据
        :param flist: user doc的 follower 或 followee list
        :param time: 目标时刻
        :return: accumulated users
        """
        if len(flist) == 0:
            return []
        elif len(flist) == 1:
            return flist[0]['uids']
        else:
            times = [fdict['time'] for fdict in flist]
            # if time is None, return all
            pos = bisect.bisect(times, time) if time else len(times)
            merge = lambda x, y: x + y
            if pos == 0:
                return flist[0]['uids']
            elif pos == len(times):
                return reduce(merge, [fdict['uids'] for fdict in flist])
            else:
                # 找到最接近time的那个时刻
                if time - times[pos-1] < times[pos] - time:
                    return reduce(merge, [fdict['uids'] for fdict in flist[:pos]])
                else:
                    return reduce(merge, [fdict['uids'] for fdict in flist[:pos+1]])


class Answer:
    USER_PREFIX = 'http://www.zhihu.com/people/'

    def __init__(self, tid, aid, IS):
        self.tid = tid
        self.aid = aid
        self.InfoStorage = IS  # Question object
        self.graph = networkx.DiGraph()
        self.root = None  # 回答节点
        self.upvoters = []
        self.commenters = []
        self.collectors = []
        self._load_answer()

    def _load_answer(self):
        """
        从数据库加载答案, 填充 up/com/col, InfoStorage.propagators
        """
        answer_doc = db[a_col(self.tid)].find_one({'aid': self.aid})
        assert answer_doc is not None
        self.answer_time = answer_doc['time']
        uid = answer_doc['answerer']
        self.root = UserAction(answer_doc['time'], self.aid, uid, ANSWER_QUESTION)
        self.add_node(self.root)
        self.upvoters = [
            UserAction(time=u['time'], aid=self.aid, uid=u['uid'], acttype=UPVOTE_ANSWER)
            for u in answer_doc['upvoters']
        ]
        self.commenters = [
            UserAction(time=u['time'], aid=self.aid, uid=u['uid'], acttype=COMMENT_ANSWER)
            for u in answer_doc['commenters']
        ]
        self.collectors = [
            UserAction(time=u['time'], aid=self.aid, uid=u['uid'], acttype=COLLECT_ANSWER)
            for u in answer_doc['collectors']
        ]
        # 插值. comment 肯定有时间信息, 不处理
        interpolate(self.upvoters)
        interpolate(self.collectors)

        propagators = self.upvoters.copy()
        propagators.insert(0, UserAction(self.answer_time, self.aid, uid, ANSWER_QUESTION))
        self.InfoStorage.add_answer_propagator(self.aid, propagators)

    def infer(self, save_to_db):
        cp = copy(self.InfoStorage.propagators)  # 防止修改IS.propagators
        propagators = []
        times = []  # bisect 不支持 key, 故只能再记录一个时间序列
        while not cp.empty():
            action = cp.get()
            if action.aid != self.aid:
                propagators.append(action)  # 排除本答案的回答/点赞者
                times.append(action.time)

        upvoters_added = [self.root]  # 记录已经加入图中的点赞者
        # 按时间顺序一起处理
        pq = PriorityQueue()
        i1 = i2 = i3 = 0

        if self.upvoters:
            pq.put(self.upvoters[0])
            i1 += 1
        if self.commenters:
            pq.put(self.commenters[0])
            i2 += 1
        if self.collectors:
            pq.put(self.collectors[0])
            i3 += 1
        l1, l2, l3 = len(self.upvoters), len(self.commenters), len(self.collectors)
        while not pq.empty():
            action = pq.get()
            if self.graph.has_node(action.uid):
                # 融合 uid 相同的点
                self.graph.node[action.uid]['acttype'] = \
                    action.acttype | self.graph.node[action.uid]['acttype']
            else:
                relation = self._infer_node(action, propagators, times, upvoters_added)
                self.add_node(relation.tail)
                self.add_edge(*relation)

            if action.acttype == UPVOTE_ANSWER and i1 < l1:
                pq.put(self.upvoters[i1])
                upvoters_added.append(action)
                i1 += 1
            elif action.acttype == COMMENT_ANSWER and i2 < l2:
                pq.put(self.commenters[i2])
                i2 += 1
            elif action.acttype == COLLECT_ANSWER and i3 < l3:
                pq.put(self.commenters[i3])
                i3 += 1

        for node in self.graph.nodes():
            self.graph.node[node]['acttype'] = get_action_type(self.graph.node[node]['acttype'])

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

        if save_to_db:
            db2.dynamic.insert(tree_data)
        else:
            with open('data/dump.json', 'w') as f:
                json.dump(tree_data, f, cls=MyEncoder, indent='\t')

    def _infer_node(self, action, propagators, times, upvoters_added):
        from client_pool import get_client
        # 所有的 user 信息都从 IS 获取
        followees = self.InfoStorage.get_user_followee(action.uid, action.time)
        followees = set(followees) if followees is not None else None

        # 从已经添加的 upvoter 推断 follow 关系, 注意要逆序扫
        for cand in reversed(upvoters_added):
            followers = self.InfoStorage.get_user_follower(cand.uid, action.time)
            if followees is not None:
                if cand.uid in followees:
                    return Relation(cand, action, RelationType.follow)
            elif followers is not None:
                if action.uid in followers:
                    return Relation(cand, action, RelationType.follow)
            else:
                logger.warning("%s lacks follower,%s lacks followee" %
                               (cand.uid, action.uid))
                u1 = get_client().author(self.USER_PREFIX + action.uid)
                u2 = get_client().author(self.USER_PREFIX + cand.uid)
                if u1.followee_num < u2.follower_num:
                    followees = self.InfoStorage.fetch_user_followee(u1)
                    if cand.uid in followees:
                        return Relation(cand, action, RelationType.follow)
                else:
                    followers = self.InfoStorage.fetch_user_follower(u2)
                    if action.uid in followers:
                        return Relation(cand, action, RelationType.follow)

        # 如果不是follow 关系, 推断 qlink+notification, 优先级 noti > qlink
        # 推断 notification
        for follow_action in self.InfoStorage.question_followers:
            if follow_action.time < self.answer_time:
                if follow_action.uid == action.uid:
                    return Relation(self.root, action, RelationType.notification)
            else:
                break  # 关注早于答案,才能收到notification

        # 作为回答者接收到新回答提醒
        if action.uid in self.InfoStorage.answers:
            if self.InfoStorage.answers[action.uid].time < action.time:
                return Relation(self.root, action, RelationType.notification)

        # 推断 qlink
        # 使用 copy 出来的 propagators
        # 取最靠近 time 的那个propagator，因为在时间线上新的东西会先被看见
        # 为了确定最接近的，使用 bisect_left 找到插入位置，左边的那个就是目标propagator
        pos = bisect.bisect_left(times, action.time)
        if pos > 0:
            for i in range(pos-1, -1, -1):
                cand = propagators[i]
                # 逻辑和推断follow完全一样,为了不重复生成followees,不单独写成函数
                followers = self.InfoStorage.get_user_follower(cand.uid, action.time)
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
                    u1 = get_client().author(self.USER_PREFIX + action.uid)
                    u2 = get_client().author(self.USER_PREFIX + cand.uid)
                    if u1.followee_num < u2.follower_num:
                        followees = self.InfoStorage.fetch_user_followee(u1)
                        if cand.uid in followees:
                            # cand is action.uid's followee
                            return Relation(self.root, action, RelationType.qlink)
                    else:
                        followers = self.InfoStorage.fetch_user_follower(u2)
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

    def add_edge(self, useraction1, useraction2, reltype):
        self.graph.add_edge(useraction1.uid, useraction2.uid, reltype=reltype)

    def load_graph(self):
        """
        加载之前生成的graph
        :return:
        """
        pass
