"""
更新uid,应对用户变换uid的情况
"""
import pymongo
from copy import deepcopy
from pprint import pprint


def change_uid_in_collection(collection, old, new):
    try:
        for doc in collection.find({}, {'_id': 0}):
            ori_doc = deepcopy(doc)
            if 'aid' in doc:
                match = {'aid': doc['aid']}
                if doc['answerer'] == old:
                    doc['answerer'] = new
                for fo in doc['upvoters']:
                    if fo['uid'] == old:
                        print(3)
                        fo['uid'] = new
                for fo in doc['commenters']:
                    if fo['uid'] == old:
                        print(2)
                        fo['uid'] = new
                for fo in doc['collectors']:
                    if fo['uid'] == old:
                        print(1)
                        fo['uid'] = new
            elif 'qid' in doc:
                match = {'qid': doc['qid']}
                if doc['asker'] == old:
                    doc['asker'] = new
                for fo in doc['follower']:
                    if fo['uid'] == old:
                        fo['uid'] = new
            elif 'uid' in doc:
                match = {'uid': doc['uid']}
                if doc['uid'] == old:
                    doc['uid'] = new
                if 'follower' in doc:
                    for group in doc['follower']:
                        if old in group['uids']:
                            index = group['uids'].index(old)
                            group['uids'][index] = new
                if 'followee' in doc:
                    for group in doc['followee']:
                        if old in group['uids']:
                            index = group['uids'].index(old)
                            group['uids'][index] = new
            else:
                raise Exception()
            if ori_doc != doc:
                pprint(ori_doc)  # 用来定位用户,找到修改后的uid
                # result = collection.replace_one(match, doc)
                # print(result.modified_count)
    except Exception as e:
        print(doc)
        raise e


def change_uid(db_name, old, new):
    db = pymongo.MongoClient('127.0.0.1', 27017).get_database(db_name)
    colls = [
        "19550517_q", "19551147_q", "19561087_q", "19553298_q",
        "19550517_a", "19551147_a", "19561087_a", "19553298_a", 'user'
    ]
    for coll in [db.get_collection(col_name) for col_name in colls]:
        change_uid_in_collection(coll, old, new)

def t_change_uid():
    old_qdoc = {
        "topic": "19551147",
        "url": "http://www.zhihu.com/question/41485064?sort=created",
        "follower": [
            {'time':None, 'uid': '1'},
            {'time':None, 'uid': '2'},
            {'time':None, 'uid': 'old_uid'}
        ],
        "asker": "old_uid",
        "title": "武汉零玖零加网络科技有限公司是真的吗可信吗？",
        "qid": "41485064"
    }
    new_qdoc = {
        "topic": "19551147",
        "url": "http://www.zhihu.com/question/41485064?sort=created",
        "follower": [
           {'time':None, 'uid': '1'},
           {'time':None, 'uid': '2'},
           {'time':None, 'uid': 'new_uid'}
        ],
        "asker": "new_uid",
        "title": "武汉零玖零加网络科技有限公司是真的吗可信吗？",
        "qid": "41485064"
    }
    old_adoc = {
        "answerer": "old_uid",
        "qid": "41021690",
        "commenters": [
            {'time':None, 'uid': '1'},
            {'time':None, 'uid': '2'},
            {'time':None, 'uid': 'old_uid'}
        ],
        "collectors": [
            {'time':None, 'uid': '1'},
            {'time':None, 'uid': '2'},
            {'time':None, 'uid': 'old_uid'}
        ],
        "topic": "19550517",
        "url": "http://www.zhihu.com/question/41021690/answer/89242009/",
        "aid": "89242009",
        "upvoters": [
            {'time':None, 'uid': '1'},
            {'time':None, 'uid': '2'},
            {'time':None, 'uid': 'old_uid'}
        ],
    }
    new_adoc = {
        "answerer": "new_uid",
        "qid": "41021690",
        "commenters": [
            {'time':None, 'uid': '1'},
            {'time':None, 'uid': '2'},
            {'time':None, 'uid': 'new_uid'}
        ],
        "collectors": [
            {'time':None, 'uid': '1'},
            {'time':None, 'uid': '2'},
            {'time':None, 'uid': 'new_uid'}
        ],
        "topic": "19550517",
        "url": "http://www.zhihu.com/question/41021690/answer/89242009/",
        "aid": "89242009",
        "upvoters": [
            {'time':None, 'uid': '1'},
            {'time':None, 'uid': '2'},
            {'time':None, 'uid': 'new_uid'}
        ],
    }
    old_udoc = {
        'uid': 'old_uid',
        'follower': [
            {
                'time': 0,
                'uids': ['1', '2', 'old_uid']
            },
            {
                'time': 1,
                'uids': ['old_uid', '3']
            }
        ],
        'followee': [
            {
                'time': 3,
                'uids': ['1', '2', 'old_uid']
            },
            {
                'time': 4,
                'uids': ['old_uid', '3']
            }
        ],
    }
    new_udoc = {
        'uid': 'new_uid',
        'follower': [
            {
                'time': 0,
                'uids': ['1', '2', 'new_uid']
            },
            {
                'time': 1,
                'uids': ['new_uid', '3']
            }
        ],
        'followee': [
            {
                'time': 3,
                'uids': ['1', '2', 'new_uid']
            },
            {
                'time': 4,
                'uids': ['new_uid', '3']
            }
        ],
    }
    db = pymongo.MongoClient('127.0.0.1', 27017).test
    qcol = db.test_q
    acol = db.test_a
    ucol = db.test_u
    qcol.insert(old_qdoc)
    acol.insert(old_adoc)
    ucol.insert(old_udoc)
    try:
        change_uid_in_collection(qcol, 'old_uid', 'new_uid')
        change_uid_in_collection(acol, 'old_uid', 'new_uid')
        change_uid_in_collection(ucol, 'old_uid', 'new_uid')
        assert qcol.find({}, {'_id':0, 'time':0})[0] == new_qdoc
        assert acol.find({}, {'_id':0, 'time':0})[0] == new_adoc
        assert ucol.find({}, {'_id':0, 'time':0})[0] == new_udoc
    finally:
        db.drop_collection('test_a')
        db.drop_collection('test_q')
        db.drop_collection('test_u')


if __name__ == '__main__':
    change_uid('train','yin-ying-43-25', 'xxxx')
    # change_uid('test', 'yin-ying-43-25', 'xxxx')
