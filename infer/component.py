"""
定义推断所使用的

方法的设计一定要支持多进程, 因为推断要使用多进程加速
从数据库加载用 load
"""
import bisect
import logging
from queue import PriorityQueue
from collections import namedtuple
from copy import copy
from typing import Union
from functools import reduce

import networkx
from common import *
from utils import *
from client_pool import get_client


logger = logging.getLogger(__name__)
# class ListNode:
#     """
#     记录 propagator, 用 linkedlist 方便使用优先队列
#     """
#     def __init__(self, val:UserAction):
#         self.val = val
#         self.next = None

# follow question 操作, aid=None
UserAction = namedtuple('UserAction', ['time', 'aid', 'uid', 'acttype'])


class InfoStorage:
    """
    用来存储动态传播图推断所需的信息,包括答案affecters, 用户关注关系
    """
    def __init__(self, tid, qid):
        self.tid = tid
        self.qid = qid
        # 记录各个答案提供的能影响其它用户的用户, 推断qlink
        self.question_followers = None  # [UserAction]
        self.answer_propagators = {}  # {aid: [UserAction]}
        self.followers = {}  # user follower, {uid: []}
        self.followees = {}  # user followee, {uid: []}
        self.propagators = PriorityQueue()

    def load_question_followers(self):
        """
        load question followers from database. 同时加入 propagators
        """
        question_doc = db[q_col(self.tid)].find_one({'qid': self.qid})
        assert question_doc is not None
        for f in question_doc['follower']:
            self.propagators.put(
                UserAction(f['time'], None, f['uid'], FOLLOW_QUESTION))

    def add_answer_propagator(self, aid, propagators):
        """
        记录每个 answer 的 upvoter+answerer. 同时加入 propagators
        :param propagators: List of UserAction
        """
        self.answer_propagators[aid] = propagators
        map(self.propagators.put, propagators)

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
        self.followers[uid] = followers

    def get_user_followee(self, uid, time=None):
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
        self.followees[uid] = followees

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

    def __init__(self, tid, aid, uid, IS):
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
        self.graph.add_node(uid, aid=self.aid, acttype=ANSWER_QUESTION,
                            time=answer_doc['time'])
        self.root = self.graph.node[uid]
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
        # TODO: 处理 time 是 None 的情况

        propagators = self.upvoters.copy()
        propagators.insert(0, UserAction(self.answer_time, self.aid, uid, ANSWER_QUESTION))
        self.InfoStorage.add_answer_propagator(self.aid, propagators)

    def infer(self):
        cp = copy(self.InfoStorage.propagators)  # 防止修改IS.propagators
        propagators = []
        while not cp.empty():
            action = cp.get()
            if action.aid != self.aid:
                propagators.append(action)  # 排除本答案的回答/点赞者

        upvoters_added = []  # 记录已经加入图中的点赞者
        # 按时间顺序一起处理
        pq = PriorityQueue()

        # TODO: 处理length=0
        map(pq.put, [self.upvoters[0], self.collectors[0], self.commenters[0]])
        i1 = i2 = i3 = 1
        l1, l2, l3 = len(self.upvoters), len(self.commenters), len(self.collectors)
        while i1 < l1 or i2 < l2 or i3 < l3:
            action = pq.get()
            self._infer_node(action, propagators, upvoters_added)
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

    def _infer_node(self, action: UserAction, propagators, upvoters_added):
        # TODO: 从本答案的upvoter推断follow 关系
        # 所有的 user 信息都从 IS 获取
        followees = self.InfoStorage.get_user_followee(action.uid, action.time)
        followees = set(followees) if followees is not None else None

        # 如果不是follow 关系, 推断 qlink+notification, 优先级 noti > qlink
        # 推断 notification
        head = self.InfoStorage.question_followers
        while head:
            follow_action = head.val  # (time, uid, type)
            if follow_action.time < self.answer_time:
                if follow_action.uid == uid:
                    return something
                else:
                    head = head.next
            else:
                break  # 关注早于答案,才能收到notification

        # 推断 qlink
        # 使用 copy 出来的 propagators
        # 取最靠近 time 的那个propagator，因为在时间线上新的东西会先被看见
        # 为了确定最接近的，使用 bisect_left 找到插入位置，左边的那个就是目标propagator
        pos = bisect.bisect_left(propagators, action.time)
        if pos > 0:
            for i in range(pos-1, -1, -1):
                cand = propagators[i]
                followers = self.InfoStorage.get_user_follower(cand.uid, action.time)
                if followees is not None:
                    if cand.uid in followees:
                        return something  # cand is action.uid's followee
                elif followers is not None:
                    if action.uid in followers:
                        return something  # action.uid is cand's follower
                else:
                    logger.warning("%s lacks follower,%s lacks followee" %
                                   (cand.uid, action.uid))
                    u1 = get_client().author(self.USER_PREFIX + action.uid)
                    u2 = get_client().author(self.USER_PREFIX + cand.uid)
                    if u1.followee_num < u2.follower_num:
                        followees = self.InfoStorage.fetch_user_followee(u1)
                        if cand.uid in followees:
                            return something  # cand is action.uid's followee
                    else:
                        followers = self.InfoStorage.fetch_user_follower(u2)
                        if action.uid in followers:
                            return something  # action.uid is cand's follower

        # 之前都不是, 只能是 recommendation 了

    def fetch_follower_followee(self):
        """
        获取缺失的 follower/followee 信息
        有可能
        1. 这个用户完全不在数据库里
        2. 这个用户在数据库里, 但是缺少 follower 或 followee 信息
        """
        url = 'https://www.zhihu.com/people/' + uid
        user = get_client().author(url)
        user._session.mount(url, HTTPAdapter(pool_connections=1, max_retries=3))
        try:
            if limit_to is None:
                if user.followee_num < 500:
                    _fetch_followees(user, datetime, db_name)

                if user.follower_num < 500:
                    _fetch_followers(user, datetime, db_name)

                if user.followee_num >= 500 and user.follower_num >= 500:
                    if user.followee_num < user.follower_num:
                        _fetch_followees(user, datetime, db_name)
                    else:
                        _fetch_followers(user, datetime, db_name)
            elif limit_to == FETCH_FOLLOWER:
                _fetch_followers(user, datetime, db_name)
            elif limit_to == FETCH_FOLLOWEE:
                _fetch_followees(user, datetime, db_name)
            else:
                raise FetchTypeError("No such type: " + str(limit_to))
        except Exception as e:
            logger.critical(user.url, exc_info=True)
            raise e.with_traceback(sys.exc_info()[2])

    def _fetch_followers(user, datetime):
        follower_num = user.follower_num
        if follower_num > 2000:
            return
        doc = user_coll.find_one({'uid': user.id}, {'follower':1, '_id':0})
        if doc is None:
            # new user
            uids = [follower.id for follower in user.followers if follower is not ANONYMOUS]
            user_coll.insert({
                'uid': user.id,
                "follower": [{
                    'time': datetime,
                    'uids': uids
                }]
            })

    def load_graph(self):
        """
        加载之前生成的graph
        :return:
        """
        pass





