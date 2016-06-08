"""
从 dynamic 中收集整理必要的数据,以供分析
"""
import pymongo
import sys
from networkx.readwrite import json_graph
from networkx import shortest_path_length, dfs_successors
from icommon import *
from user import UserManager
import zhihu_oauth
from zhihu_oauth import ZhihuClient
from client import client
from itertools import chain

from iutils import transform_outgoing

db = pymongo.MongoClient('127.0.0.1', 27017).get_database('analysis')
usermanager = UserManager(db.user)
answer_coll = db.answer
influence_coll = db.influence
receiver_coll = db.receiver


def get_info_from_dynamic_graph(aid, graph, answerer, links):
    """
    :param data: dynamic graph read from database
    :return:
    传播层数,四种关系的数量,回答者粉丝数,每个非叶节点影响的用户数量
    answer {
        fo_count: 回答者粉丝数(maybe None),
        layer: 传播层数,
        1: ,
        2: ,
        3: ,
        4: ,
        upvote_num:
        comment_num:
    }
    influence {fo_count: x, succ_count: y}
    receiver {'fo_count': answerer_follower_count, 'time': sorted times}
    """
    max_dis = 0
    answer = {'aid': aid}
    influence = []
    receiver = None

    for uid in graph.nodes():
        node_data = graph.node[uid]
        max_dis = max(max_dis, shortest_path_length(graph, answerer, uid))
        if uid != answerer:
            fo = usermanager.get_user_follower(uid, node_data['time'])
            if fo is not None:
                fo_count = len(fo)
            else:
                try:
                    u = client.people(uid)
                    fo_count = u.follower_count
                except zhihu_oauth.exception.GetDataErrorException:
                    continue
            succ_count = 0
            for _, successors in dfs_successors(graph, uid).items():
                succ_count += len(successors)
            influence.append({'fo_count': fo_count,'succ_count': succ_count})

    answer['layer'] = max_dis
    answer_time = graph.node[answerer]['time']
    if answerer == '':  # 匿名
        answerer_follower_count = None
    else:
        fo = usermanager.get_user_follower(answerer, answer_time)
        try:
            answerer_follower_count = len(fo) if fo else client.people(answerer).follower_count
        except zhihu_oauth.exception.GetDataErrorException:
            return
    answer['fo_count'] = answerer_follower_count

    if graph.number_of_nodes() >= 100:
        times = []
        for uid in graph.nodes():
            times.append(graph.node[uid]['time'])
        times.sort()
        receiver = {
            'fo_count': answerer_follower_count, 'time': times
        }

    rel_count = {
        str(RelationType.follow): 0,
        str(RelationType.notification): 0,
        str(RelationType.qlink): 0,
        str(RelationType.recommendation): 0
    }
    for link in links:
        rel_count[str(link['reltype'])] += 1

    answer.update(rel_count)

    answer_coll.insert(answer)
    for data in influence:
        influence_coll.insert(data)
    if receiver:
        receiver_coll.insert(receiver)


def coll_all_data():
    """
    从dynamic结果中收集数据
    :return:
    """
    # remove existing data
    # answer_coll.remove()
    # influence_coll.remove()
    # receiver_coll.remove()
    it = chain(db.dynamic_test.find(), db.dynamic.find())
    for i, adoc in enumerate(it):
        aid = adoc['aid']
        tree_data = transform_outgoing(adoc)
        dynamic_graph = json_graph.tree_graph(tree_data)
        get_info_from_dynamic_graph(aid, dynamic_graph, tree_data['id'], tree_data['links'])
        print(i)


def add_extra_info():
    """
    添加之前没有添加的信息
    """
    for adoc in answer_coll.find({}, {'aid': 1}):
        aid = adoc['aid']
        full_doc = db.all_a.find_one({'aid': aid}, {'collectors': 1})
        # upvote_num = len(full_doc['upvoters'])
        # comment_num = len(full_doc['commenters'])
        collect_num = len(full_doc['collectors'])
        answer_coll.update({'aid': aid},
                           {'$set': {
                               # 'upvote_num': upvote_num,
                               # 'comment_num': comment_num,
                               'collect_num': collect_num
                           }})

if __name__ == '__main__':
    # coll_all_data()
    add_extra_info()