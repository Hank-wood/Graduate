import sys

import pymongo
from iutils import *
from component import InfoStorage, Answer


def test_dump_json():
    import networkx
    from datetime import datetime
    from networkx.readwrite import json_graph

    G = networkx.DiGraph()
    G.add_node(1, type='answer', time=datetime.now())
    G.add_node(2, type='upvote', time=datetime.now())
    G.add_edge(1, 2)
    data = json_graph.tree_data(G, root=1)
    import json

    class MyEncoder(json.JSONEncoder):

        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()

            return json.JSONEncoder.default(self, obj)

    with open('dump.json', 'w') as f:
        json.dump(data, f, cls=MyEncoder)


def infer_one_question(tid, qid, db_name):
    sys.modules['component'].__dict__['db'] = \
        pymongo.MongoClient('127.0.0.1', 27017).get_database(db_name)
    info_storage = InfoStorage(tid, qid)
    db = pymongo.MongoClient('127.0.0.1:27017').get_database(db_name)
    collection = db.get_collection(a_col(tid))

    answers = []
    for answer_doc in collection.find({'qid': qid}, {'aid': 1}):
        answers.append(Answer(tid, answer_doc['aid'], info_storage))

    answers[0].infer()

if __name__ == '__main__':
    infer_one_question(tid='19551147', qid='40554112', db_name='zhihu_data_0219')
