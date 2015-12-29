import os
from datetime import datetime
from collections import deque

import requests
import json

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


def validate_config(config=None):
    import json
    import requests
    config = config if (config and isinstance(config, dict)) else \
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


def validate_cookie(cookie_file):
    """
    :param cookie_file: file path of cookie
    :return: True for valid, False for invalid
    """
    session = requests.Session()
    if os.path.isfile(cookie_file):
        with open(cookie_file) as f:
            cookies = f.read()
            cookies_dict = json.loads(cookies)
            session.cookies.update(cookies_dict)
            res = session.get('https://zhihu.com')
            history = res.history
            session.close()
            return res.status_code == 200 and history[0].status_code == 301 \
                    and history[1].status_code == 302
    else:
        raise IOError("no such cookie file:" + cookie_file)
