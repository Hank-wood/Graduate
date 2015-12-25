# coding: utf-8

import time
import threading
import atexit
from datetime import datetime

import zhihu

from monitor import TopicMonitor
from utils import *
from utils import task_queue

# TODO: logging


class TaskLoop(threading.Thread):

    def run(self):
        while True:
            time.sleep(10)  # TODO: set to 60s
            count = len(task_queue)
            for _ in range(count):
                task = task_queue.popleft()
                task.execute()


def main():
    client = zhihu.ZhihuClient('../cookies/zhuoyi.json')
    TaskLoop().start()
    m = TopicMonitor(client)
    while True:
        # TODO: 考虑新问题页面采集消耗的时间，不能 sleep 60s
        time.sleep(5)
        print(now_string())
        m.detect_new_question()


def cleaning():
    """
    Only for testing
    """
    from db import DB
    print("exit")
    for collection in DB.db.collection_names():
        db[collection].drop()


if __name__ == '__main__':
    main()
    # atexit.register(cleaning)