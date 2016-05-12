import pymongo
import sys
from networkx.readwrite import json_graph
from networkx import shortest_path_length, dfs_successors
from icommon import *
from user import UserManager
from zhihu_oauth import ZhihuClient
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

recommendation_count = 0
for node in static_graph.nodes(data=True):
    if 'UPVOTE_ANSWER' in node[1]['acttype']:
        edge = static_graph.in_edges(node[0])[0]
        print('(' + edge[1] + ',' + str(static_links[edge]) + '),', end='')
        # if static_links[edge] == RelationType.recommendation:
        #     recommendation_count += 1

