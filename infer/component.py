"""
定义推断所使用的

方法的设计一定要支持多进程, 因为推断要使用多进程加速
从数据库加载用 load
"""
from queue import PriorityQueue

import networkx
from common import *
from utils import *
from client_pool import get_client

class ListNode:
    """
    记录 propagator, 用 linkedlist 方便使用优先队列
    """
    def __init__(self, val):
        self.val = val
        self.next = None


class InfoStorage:
    """
    用来存储动态传播图推断所需的信息,包括答案affecters, 用户关注关系
    """
    def __init__(self, tid, qid):
        self.tid = tid
        self.qid = qid
        # 记录各个答案提供的能影响其它用户的用户, 推断qlink
        self.question_followers = None  # linked list
        self.answer_propagators = {}  # {aid: linked list}
        self.followers = {}  # user follower, {uid: []}
        self.followees = {}  # user followee, {uid: []}

    def load_question_followers(self):
        """
        load question followers from database
        """
        pass

    def add_answer_propagator(self, aid, propagators):
        """
        记录每个 answer 的 upvoter+answerer
        :param propagators: ListNode((time, uid, type))
        """
        self.answer_propagators[aid] = propagators

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
        self.root = networkx.node(uid, ANSWER_QUESTION)
        self.graph.add_node(self.root)
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
        self.upvoters = answer_doc['upvoters']
        self.commenters = answer_doc['commenters']
        self.collectors = answer_doc['collectors']
        # TODO: gen propagators use answerer and upvoters, ListNode((time, uid, type))
        propagators = []
        self.InfoStorage.add_answer_propagator(self.aid, propagators)

    def infer(self):
        pq = PriorityQueue()
        # 先从 upvoters 入手? 还是按时间顺序一起处理


    def _infer_node(self, uid, time):
        # TODO: 从本答案的upvoter推断follow 关系

        # 如果不是follow 关系, 推断 qlink+notification, 优先级 noti > qlink
        # 推断 notification
        head = self.InfoStorage.question_followers
        while head:
            value = head.val  # (time, uid, type) #TODO: 试试namedtuple能否在pq 起作用
            if value[0] < self.answer_time:
                if value[1] == uid:
                    # 找到了
                    return something
                else:
                    head = head.next
            else:
                break  # 关注早于答案,才能收到notification

        # 推断 qlink
        # TODO: 把 self.IS.followers 和 self.answer_propagaters 加入优先队列


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





