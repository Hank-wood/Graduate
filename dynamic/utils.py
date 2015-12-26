from datetime import datetime
from collections import deque


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


def check_valid_config():
    dynamic_config_file = '/Users/laike9m/ICT/zhihu-analysis/dynamic/config/dynamic_config.json'
    import json
    import requests
    config = json.load(open(dynamic_config_file, encoding='utf-8'))

    # check topics are valid
    assert 'topics' in config
    for topic in config['topics']:
        code = requests.get('https://www.zhihu.com/topic/' + topic).status_code
        if code == 404:
            raise Exception("invalid url")  # TODO: replace with my exception
        assert code == 200

    assert config['restart'] == False or config['restart'] == True
