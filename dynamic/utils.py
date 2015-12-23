from datetime import datetime
from collections import deque

task_queue = deque()


def q_col(tid):
    return qid + '_q'


def a_col(tid):
    return tid + '_a'


def get_time_string(t):
    return t.strftime("%Y-%m-%d %H:%M:%S")


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_datetime(time_string):
    datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")