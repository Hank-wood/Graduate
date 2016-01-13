import os
import json
from datetime import datetime, timedelta
from pprint import pprint

import requests

from common import *


def is_q_col(collection_name):
    return collection_name.endswith('_q')


def is_a_col(collection_name):
    return collection_name.endswith('_a')


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


def get_datetime_full_string(time_string):
    """
    :param time_string: 2016-01-01 04:35:45
    """
    return datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")


def get_datetime_hour_min_sec(time_string):
    """
    :param time_string: 04:35:45
    :return: datetime(now.year, now.month, now.day, 4, 35, 45)

    如果来的 time_string 正好接近跨天,比如 23:59,则datetime.now()的date很可能是
    真实 date+1d,故需要考虑这种特殊情况
    """
    actual_time = datetime.strptime(time_string, "%H:%M:%S").time()
    now = datetime.now()
    now_day, now_time = now.date(), now.time()
    if actual_time < now_time:  # 同一天
        return datetime.combine(now_day, actual_time)
    else:  # 跨天!!
        return datetime.combine(now_day - timedelta(1), actual_time)


def get_datetime_day_month_year(time_string):
    """
    :param time_string: 2016-01-01
    :return: datetime(2016, 1, 1, 0, 0, 0)
    """
    year, month, day = time_string.split('-')
    return datetime(int(year), int(month), int(day), 0, 0, 0)


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
            session.close()
            return '首页' in res.text
    else:
        raise IOError("no such cookie file:" + cookie_file)


def answer_deleted(answer_url):
    return requests.get(answer_url).history[0].status_code == 302


def dict_equal(dict_more_key, dict_less_key):
    try:
        for key in dict_less_key:
            if not dict_more_key[key] == dict_less_key[key]:
                print("unequal key: " + key)
                pprint(dict_more_key[key])
                pprint(dict_less_key[key])
                return False
    except KeyError:
        return False

    return True


def list_of_dict_equal(list_of_dict_more_key, list_of_dict_less_key):
    from collections import Iterable
    if not isinstance(list_of_dict_more_key, Iterable) or \
        not isinstance(list_of_dict_less_key, Iterable):
        raise Exception("not iterable")
    # deprecated function
    pass


__all__ = [
    'a_col', 'q_col', 'get_time_string', 'now_string',
    'get_datetime_day_month_year', 'get_datetime_hour_min_sec',
    'get_datetime_full_string', 'validate_config', 'validate_cookie',
    'answer_deleted', 'dict_equal', 'is_a_col', 'is_q_col'
]