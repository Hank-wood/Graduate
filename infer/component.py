"""
定义推断所使用的

方法的设计一定要支持多进程, 因为推断要使用多进程加速
从数据库加载用 load
"""
import bisect
from queue import PriorityQueue
from collections import namedtuple
from copy import copy

import networkx
from common import *
from utils import *
from client_pool import get_client


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

    def get_user_follower(self, uid):
        return self.followers.get(uid, None)

    def set_user_follower(self, uid, followers):
        self.followers[uid] = followers

    def get_user_followee(self, uid):
        return self.followees.get(uid, None)

    def set_user_followee(self, uid, followees):
        self.followees[uid] = followees

class Answer:
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

        # 推断 qlink,
        # 使用 copy 出来的 propagators
        # 取最靠近 time 的那个propagator，因为在时间线上新的东西会先被看见
        # 为了确定最接近的，使用 bisect_left 找到插入位置，左边的那个就是目标propagator
        pos = bisect.bisect_left(propagators, action.time)
        if pos > 0:
            for i in range(pos-1, -1, -1):
                cand = propagators[i]
                if action.uid in self.get_user_followers(cand.uid):
                    return something  # 找到了

    @staticmethod
    def get_user_followers(uid):
        user_doc = db['user'].find_one({'uid': uid}, {'follower': 1, '_id': 0})
        if user_doc is None:
            self.fetch_follower(uid)
        # TODO:


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





