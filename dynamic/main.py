# coding: utf-8

import time
import threading
import atexit
from datetime import datetime

import zhihu

from monitor import TopicMonitor
from utils import *
from utils import task_queue
from common import *
from config.dynamic_config import restart
from db import DB


class TaskLoop(threading.Thread):

    def __init__(self, routine=None, *args, **kwargs):
        self.routine = routine
        super().__init__(*args, **kwargs)

    def run(self):
        while True:
            if self.routine and callable(self.routine):
                self.routine()
            time.sleep(10)  # TODO: set to 60s
            count = len(task_queue)
            for _ in range(count):
                task = task_queue.popleft()
                task.execute()


def main(routine=None):
    if restart:
        DB.drop_all_collections()

    client = zhihu.ZhihuClient('../cookies/zhuoyi.json')
    TaskLoop(daemon=True).start()
    m = TopicMonitor(client)
    count = 0
    while True:
        # TODO: 考虑新问题页面采集消耗的时间，不能 sleep 60s
        try:
            if routine and callable(routine):
                print("invoke routine with count: " + str(count))
                routine(count)
        except EndProgramException:
            break

        time.sleep(5)
        print(now_string())
        m.detect_new_question()
        count += 1


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