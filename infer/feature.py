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

class StaticData:

    def __init__(self):
        pass

    def load_from_dynamic(self):
        """
        加载标注好的动态传播图
        """
        # TODO: 还是没有决定要怎么存



