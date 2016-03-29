"""
定义推断所使用的

方法的设计一定要支持多进程, 因为推断要使用多进程加速
从数据库加载用 load
"""
import bisect
import logging
import json
import shutil
from queue import PriorityQueue
from copy import copy
from datetime import datetime
from os import path
from threading import Thread
from time import sleep
from itertools import groupby


import networkx
from networkx.readwrite import json_graph

from icommon import *
from iutils import *


logger = logging.getLogger(__name__)


class DynamicQuestionWithAnswer:
    """
    用来存储动态传播图推断所需的信息,包括答案affecters, 用户关注关系
    """
    def __init__(self, tid, qid):
        self.tid = tid
        self.qid = qid
        # 记录各个答案提供的能影响其它用户的用户, 推断qlink
        self.question_followers = []  # [UserAction]
        self.answers = {}  # {uid: UserAction(acttype=ANSWER_QUESTION)}
        self.propagators = PriorityQueue()
        self.load_question_followers()
        self.user_actions = {}  # 记录所有 user action for qlink match

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
            follow_action = UserAction(f['time'], '', f['uid'], FOLLOW_QUESTION)
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

    def add_user_actions(self, user_actions: dict):
        for key, value in user_actions.items():
            self.user_actions[key] = self.user_actions.get(key, []) + value
            self.user_actions[key].sort(key=lambda x: x.time)


class DynamicAnswer:
    def __init__(self, tid, aid, dqa):
        self.tid = tid
        self.aid = aid
        self.dqa = dqa  # dynamic question with answer
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
        self.dqa.add_answer_propagator(self.aid, propagators)

        # fill user_actions
        all_user_actions = [self.root] + self.upvoters + self.commenters + self.collectors
        key = lambda x: x.uid
        all_user_actions.sort(key=key)
        user_actions = {}
        for key, group in groupby(all_user_actions, key=key):
            if key != '':  # 排除匿名
                user_actions[key] = list(group)
        self.dqa.add_user_actions(user_actions)

    def infer(self, save_to_db):
        cp = copy(self.dqa.propagators)  # 防止修改IS.propagators
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
                pq.put(self.collectors[i3])
                i3 += 1

        for node in self.graph.nodes():
            self.graph.node[node]['acttype'] = acttype2str(self.graph.node[node]['acttype'])

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
            db2.dynamic.replace_one({'aid': self.aid},
                                    trans_before_save(tree_data),
                                    upsert=True)
        else:
            with open('data/dump.json', 'w') as f:
                json.dump(tree_data, f, cls=MyEncoder, indent='\t')

    def _infer_node(self, action, propagators, times, upvoters_added):
        from client_pool2 import get_client2 as get_client
        # 所有的 user 信息都从 IS 获取
        followees = user_manager.get_user_followee(action.uid, action.time)
        followees = set(followees) if followees is not None else None

        # 从已经添加的 upvoter 推断 follow 关系, 注意要逆序扫
        for cand in reversed(upvoters_added):
            if cand.uid == '':  # 匿名回答者
                continue
            followers = user_manager.get_user_follower(cand.uid, action.time)
            if followees is not None:
                if cand.uid in followees:
                    return Relation(cand, action, RelationType.follow)
            elif followers is not None:
                if action.uid in followers:
                    return Relation(cand, action, RelationType.follow)
            else:
                logger.warning("%s lacks follower,%s lacks followee" %
                               (cand.uid, action.uid))
                u2 = get_client().author(USER_PREFIX + cand.uid)
                u1 = get_client().author(USER_PREFIX + action.uid)
                if u1.followee_num < u2.follower_num:
                    followees = user_manager.fetch_user_followee(u1)
                    if cand.uid in followees:
                        return Relation(cand, action, RelationType.follow)
                else:
                    followers = user_manager.fetch_user_follower(u2)
                    if action.uid in followers:
                        return Relation(cand, action, RelationType.follow)

        # 如果不是follow 关系, 推断 qlink+notification, 优先级 noti > qlink
        # 推断 notification
        for follow_action in self.dqa.question_followers:
            if follow_action.time < self.answer_time:
                if follow_action.uid == action.uid:
                    return Relation(self.root, action, RelationType.notification)
            else:
                break  # 关注早于答案,才能收到notification

        # 作为回答者接收到新回答提醒
        if action.uid in self.dqa.answers:
            if self.dqa.answers[action.uid].time < action.time \
                    and self.dqa.answers[action.uid].time < self.answer_time:
                return Relation(self.root, action, RelationType.notification)

        # 推断 qlink
        # 如果在另一个回答中出现了同一个uid, 不论是ans/up/cm/col, 都可直接判定 qlink 关系
        # 当然还得满足时间关系. 此时 Relation 的 head 设置成另一个回答里同uid 的 action
        for i, cand in enumerate(self.dqa.user_actions[action.uid]):
            if cand.time >= action.time:
                if i > 0:
                    # at least one action is ahead of current action
                    return Relation(self.root, action, RelationType.qlink)
                break

        # 使用 copy 出来的 propagators
        # 取最靠近 time 的那个propagator，因为在时间线上新的东西会先被看见
        # 为了确定最接近的，使用 bisect_left 找到插入位置，左边的那个就是目标propagator
        pos = bisect.bisect_left(times, action.time)
        if pos > 0:
            for i in range(pos-1, -1, -1):
                cand = propagators[i]
                if cand.uid == '':  # 匿名回答者
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

    def add_edge(self, useraction1, useraction2, reltype):
        self.graph.add_edge(useraction1.uid, useraction2.uid, reltype=reltype)

    @classmethod
    def load_and_display_graph(cls, aid):
        """
        加载之前生成的graph, dump to json, 在浏览器中显示
        """
        def load_one():
            tree_data = db2.dynamic.find_one({'aid': aid}, {'_id': 0})
            filename = path.join('data', aid + '.json')
            with open(filename, 'w') as f:
                json.dump(tree_data, f, cls=MyEncoder, indent='\t')
            shutil.copy(filename, 'data/dump.json')

            import webbrowser
            webbrowser.open_new_tab('http://127.0.0.1:8000/diffussion_tree.html')
            sleep(2)

        cls.display(operation=load_one)

    @classmethod
    def load_and_display_random_graphs(cls, n=5):
        """
        随机选择n个图显示.
        """
        def load_n():
            from random import sample
            aids = [d['aid'] for d in db2.dynamic.find({}, {'_id': 0, 'aid': 1})]
            choosen = sample(aids, k=n)
            for aid in choosen:
                tree_data = db2.dynamic.find_one({'aid': aid}, {'_id': 0})
                filename = path.join('data', aid + '.json')
                with open(filename, 'w') as f:
                    json.dump(tree_data, f, cls=MyEncoder, indent='\t')

                os.remove('data/dump.json')
                shutil.copy(filename, 'data/dump.json')

                import webbrowser
                webbrowser.open_new_tab('http://127.0.0.1:8000/diffussion_tree.html')
                sleep(2)

        cls.display(operation=load_n)

    @staticmethod
    def display(operation):
        def start_server():
            import http.server
            import socketserver
            PORT = 8000
            Handler = http.server.SimpleHTTPRequestHandler
            httpd = socketserver.TCPServer(("", PORT), Handler)
            print("serving at port", PORT)
            httpd.serve_forever()

        t = Thread(target=start_server, daemon=True)
        t.start()
        sleep(1)
        operation()

if __name__ == '__main__':
    DynamicAnswer.load_and_display_graph('87423946')
    # DynamicAnswer.load_and_display_random_graphs()