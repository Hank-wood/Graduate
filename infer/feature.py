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

一个问题及所有答案要一起加载，因为有跨答案的特征。这个统一形式应该只包含能从静态问答中
获取的信息。
问题的所有信息删除 question follower 时间
comment 四元组
collect 四元组
answer 四元组删除，time = None

提取的 feature 只是为了推断 follow，用不到 question 和其它 answer 的信息
"""

from icommon import *
from iutils import *


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

    def load_from_dynamic(self):
        """
        从 zhihu_data 加载 answer 信息
        """
        # TODO: db 从外部加载
        answer_doc = db[a_col(self.tid)].find_one({'aid': self.aid})
        assert answer_doc is not None
        self.answer_time = answer_doc['time']

        # 和 dynamic 不同, upvote time 设置成 None
        self.upvoters = [
            UserAction(None, self.aid, u['uid'], UPVOTE_ANSWER)
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

    def load_from_static(self):
        """
        从抓取的静态答案数据库加载 answer
        """
        pass

    def gen_edges(self):
        """
        生成候选边
        顺序, answerer -> up1 -> up2 -> ... -> upn, 分别作为候选边的起点
        """
        # TODO: 决定候选边的顺序
        pass

    def gen_features(self):
        """
        生成 features
        :return: n_samples * n_features vector
        """
        pass

    def gen_samples(self):
        """
        只有当用来从 dynamic 数据训练时才使用此方法
        :return: 0, 1 序列表示某关注关系是否是 follow relation
        """
        pass


class StaticQuestionWithAnswer:
    """
    表示一个静态问题和它的所有答案, 用于启发式推断 qlink, noti, recomm
    """
    def __init__(self):
        pass

