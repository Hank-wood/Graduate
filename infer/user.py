import bisect
from functools import reduce
from typing import Union


class UserManager:
    """
    管理 user
    """
    def __init__(self, coll, capacity=1000):
        self.coll = coll    # user collection
        self.followers = {}  # user follower, {uid: []}
        self.followees = {}  # user followee, {uid: []}
        self.lru = LRUCache(capacity)  # followee 和 follower 共用

    def shrink(self):
        self.followers = {
            node.key: self.followers[node.key] for node in self.lru.hashtable
            if node.key in self.followers
        }
        self.followees = {
            node.key: self.followees[node.key] for node in self.lru.hashtable
            if node.key in self.followees
        }

    def reset_capacity(self, new_capacity: int):
        assert new_capacity > 0
        self.lru.cap = new_capacity

    def get_user_follower(self, uid, time=None) -> Union[list, None]:
        """
        逻辑非常复杂
        if uid in self.followers, 返回 self.followers[uid]
        else
            if 数据库中有doc且有follower, 更新self.followers, 返回follower, 可为[]
            if 数据库中有doc但不包含follower, 返回None, self.followers[uid]=None
            if 数据库中没有doc, 返回None, self.followers[uid]=None
        time 指取到哪个时刻的follower
        """
        self.lru.set(uid)
        if uid in self.followers:
            if self.followers[uid] is None:
                return None
            else:
                return self.get_closest_users(self.followers[uid], time)

        user_doc = self.coll.find_one({'uid': uid}, {'follower': 1, '_id': 0})
        if user_doc is None:
            self.followers[uid] = None
            return None
        else:
            if 'follower' in user_doc:
                self.followers[uid] = user_doc['follower']
                return self.get_closest_users(user_doc['follower'], time)
            else:
                self.followers[uid] = None
                return None

    def fetch_user_follower(self, user) -> list:
        """
        之前没有follower, 要重新抓取, 返回抓到的, 并更新 self.followers
        """
        self.lru.set(user.id)
        uids = [er.id for er in user.followers if er is not ANONYMOUS]
        self.coll.update_one({
            'uid': user.id,
        }, {
            "$set": {
                "follower": [{
                    'time': datetime.now(),
                    'uids': uids
                }]
            }
        }, upsert=True)
        self.followers[user.id] = [{'time': datetime.now(), 'uids': uids}]
        return self.followers[user.id]

    def get_user_followee(self, uid, time=None) -> Union[list, None]:
        """
        逻辑同 get_user_followee
        """
        self.lru.set(uid)
        if uid in self.followees:
            if self.followees[uid] is None:
                return None
            else:
                return self.get_closest_users(self.followees[uid], time)

        user_doc = self.coll.find_one({'uid': uid}, {'followee': 1, '_id': 0})
        if user_doc is None:
            self.followees[uid] = None
            return None
        else:
            if 'followee' in user_doc:
                self.followees[uid] = user_doc['followee']
                return self.get_closest_users(user_doc['followee'], time)
            else:
                self.followees[uid] = None
                return None

    def fetch_user_followee(self, user) -> list:
        self.lru.set(user.id)
        uids = [ee.id for ee in user.followees if ee is not ANONYMOUS]
        self.coll.update_one({
            'uid': user.id,
        }, {
            "$set": {
                "followee": [{
                    'time': datetime.now(),
                    'uids': uids
                }]
            }
        }, upsert=True)
        self.followees[user.id] = [{'time': datetime.now(), 'uids': uids}]
        return self.followees[user.id]

    @staticmethod
    def get_closest_users(flist, time) -> list:
        """
        调用此方法时, 数据库中已经确保有相应数据
        :param flist: user doc的 follower 或 followee list
        :param time: 目标时刻
        :return: accumulated users
        """
        if len(flist) == 0:
            return []
        elif len(flist) == 1:
            return flist[0]['uids']
        else:
            times = [fdict['time'] for fdict in flist]
            # if time is None, return all
            if None in times:
                pos = len(times)
            else:
                pos = bisect.bisect(times, time) if time else len(times)
            merge = lambda x, y: x + y
            if pos == 0:
                return flist[0]['uids']
            elif pos == len(times):
                return reduce(merge, [fdict['uids'] for fdict in flist])
            else:
                # 找到最接近time的那个时刻
                if time - times[pos-1] < times[pos] - time:
                    return reduce(merge, [fdict['uids'] for fdict in flist[:pos]])
                else:
                    return reduce(merge, [fdict['uids'] for fdict in flist[:pos+1]])


class Node():
    def __init__(self, key=None, next=None, prev=None):
        self.key = key
        self.next = next
        self.prev = prev    # time limit exceed if don't use prev


class LRUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.hashtable = {}
        self.head, self.tail = Node(-1), Node(-1)
        self.head.next = self.tail
        self.tail.prev = self.head

    def pop_front(self):
        del self.hashtable[self.head.next.key]
        self.head.next = self.head.next.next
        self.head.next.prev = self.head

    def push_back(self, key):
        new_node = Node(key)
        self.hashtable[key] = new_node
        self.move_to_tail(new_node)

    def move_to_tail(self, node):
        # key is to keep node a new node before invoking move_to_tail
        prev = self.tail.prev
        node.prev, node.next = prev, self.tail
        prev.next = node
        self.tail.prev = node

    # TODO: 适应 reset cap
    def set(self, key):
        if key not in self.hashtable:
            if len(self.hashtable) >= self.cap:
                self.pop_front()
            self.push_back(key)
        else:
            node = self.hashtable[key]
            node.prev.next = node.next
            node.next.prev = node.prev
            self.move_to_tail(node)