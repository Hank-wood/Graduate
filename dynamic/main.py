# coding: utf-8

import time
import threading
from datetime import datetime

import zhihu

from monitor import TopicMonitor
from utils import *
from utils import task_queue

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


if __name__ == '__main__':
    main()