"""
统计, 分析水军
"""
import pymongo
import sys
from networkx.readwrite import json_graph
from networkx import shortest_path_length, dfs_successors
from icommon import *
from user import UserManager
from client import client

from iutils import transform_outgoing

db = pymongo.MongoClient('127.0.0.1', 27017).get_database('analysis')
usermanager = UserManager(db.user)
static_water = db.static_water
water_tree_data = transform_outgoing(static_water.find_one({'aid': '61219684'}))
static_links = {
    (l['source'], l['target']): l['reltype']
    for l in water_tree_data['links']
    }
static_graph = json_graph.tree_graph(water_tree_data)

"""
for node in static_graph.nodes(data=True):
    if 'UPVOTE_ANSWER' in node[1]['acttype']:
        edge = static_graph.in_edges(node[0])[0]
        print(edge + (static_links[edge], ))
"""



def get_info_from_dynamic_graph(graph, answerer, links):
    """
    :param data: dynamic graph read from database
    :return:
    传播层数,四种关系的数量,回答者粉丝数,每个非叶节点影响的用户数量
    answer {fo_count: 回答者粉丝数, 'layer': 传播层数, 1: ,2: ,3: ,4: }
    influence {fo_count: x, succ_count: y}
    receiver {'fo_count': answerer_follower_count, 'time': sorted times}
    """
    max_dis = 0
    answer = {}
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
                u = client.author(USER_PREFIX + uid)
                fo_count = u.follower_num
                print(fo_count)
            succ_count = 0
            for _, successors in dfs_successors(graph, uid).items():
                succ_count += len(successors)
            influence.append({'fo_count': fo_count,'succ_count': succ_count})

    print(max_dis)
    answer['layer'] = max_dis
    answer_time = graph.node[answerer]['time']
    answerer_follower_count = usermanager.get_user_follower(answerer, answer_time)
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
        RelationType.follow.value: 0,
        RelationType.notification.value: 0,
        RelationType.qlink.value: 0,
        RelationType.recommendation.value: 0
    }
    for link in links:
        rel_count[link['reltype'].value] += 1

    answer.update(rel_count)

    answer_coll.insert(answer)
    for data in influence:
        influence_coll.insert(data)
    if receiver:
        receiver_coll.insert(receiver)



get_info_from_dynamic_graph(static_graph, water_tree_data['id'], water_tree_data['links'])
