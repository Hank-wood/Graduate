# coding: utf-8

import time
import threading
from collections import deque

import zhihu

from monitor import TopicMonitor


task_queue = deque()

class TaskLoop(threading.Thread):

    def run(self):
        while True:
            time.sleep(10)  # TODO: set to 60s
            count = len(task_queue)
            print("check tasks and run")
            for _ in range(count):
                task = task_queue.popleft()
                task.execute()


def main():
    client = zhihu.ZhihuClient('../cookies/zhuoui.json')
    TaskLoop().start()
    m = TopicMonitor(client, task_queue)
    while True:
        # TODO: 考虑新问题页面采集消耗的时间，不能 sleep 60s
        time.sleep(5)
        m.detect_new_question()


if __name__ == '__main__':
    main()