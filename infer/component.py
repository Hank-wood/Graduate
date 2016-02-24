"""
定义推断所使用的

方法的设计一定要支持多进程, 因为推断要使用多进程加速
"""
import networkx
from common import *
from client_pool import get_client


class InfoStorage:
    """
    用来存储动态传播图推断所需的信息,包括答案affecters, 用户关注关系
    """
    def __init__(self, tid, qid):
        self.tid = tid
        self.qid = qid
        # 记录各个答案提供的能影响其它用户的用户, 推断qlink
        self.answer_data = {
            'follower': []
        }
        self.followers = {}  # user follower
        self.followees = {}  # user followee

    def add_users_from_answer(self, answer):
        pass


class Answer:
    def __init__(self, tid, aid, uid, q):
        self.tid = tid
        self.aid = aid
        self.q = q  # Question object
        self.graph = networkx.DiGraph()
        self.root = networkx.node(uid, ANSWER_QUESTION)
        self.graph.add_node(self.root)
        self.user_data = {
            'upvoters': [],
            'commenters': [],
            'collectors': []
        }

    def infer(self, question_data):
        pass

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





