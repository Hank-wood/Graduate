if __name__ == '__main__':
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
