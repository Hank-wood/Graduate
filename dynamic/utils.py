import os
from datetime import datetime
from collections import deque

from common import *

task_queue = deque()


def q_col(tid):
    # get question collection name
    return tid + '_q'


def a_col(tid):
    # get answer collection name
    return tid + '_a'


def get_time_string(t):
    return t.strftime("%Y-%m-%d %H:%M:%S")


def now_string():
    return datetime.now().strftime("%H:%M:%S")


def get_datetime(time_string):
    datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")


def check_valid_config(config=None):
    import json
    import requests
    config = config if config else \
             json.load(open(dynamic_config_file, encoding='utf-8'))

    if 'topics' not in config:
        raise LackConfig

    # check topics are valid
    for topic in config['topics']:
        code = requests.get('https://www.zhihu.com/topic/' + topic).status_code
        if code == 404:
            raise InvalidTopicId
        assert code == 200

    if 'restart' not in config:
        raise LackConfig

    assert config['restart'] == False or config['restart'] == True
    return True