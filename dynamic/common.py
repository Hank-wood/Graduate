import os
from collections import deque

import zhihu
import ezcf
from config.dynamic_config import topics, TASKLOOP_INTERVAL, \
                MAX_TASK_EXECUTION_TIME, FETCH_QUESTION_INTERVAL
from zhihu import ANONYMOUS

task_queue = deque()

# zhihu-analysis folder
ROOT = os.path.dirname(os.path.dirname(__file__))
test_cookie = os.path.join(ROOT, 'cookies/zhuoyi.json')
dynamic_config_file = os.path.join(ROOT, 'dynamic/config/dynamic_config.json')
logging_config_file = os.path.join(ROOT, 'dynamic/config/logging_config.json')
TOPIC_PREFIX = "https://www.zhihu.com/topic/"
QUESTION_PREFIX = "https://www.zhihu.com/question/"
FETCH_FOLLOWER = 1
FETCH_FOLLOWEE = 2

if hasattr(os, '_called_from_test'):
    TASKLOOP_INTERVAL = 5
    MAX_TASK_EXECUTION_TIME = 4
    FETCH_QUESTION_INTERVAL = 5
    topics = {"1234": "test_topic"}
    test_tid = '1234'
    test_tid2 = '5678'


if not os.path.exists(os.path.join(ROOT, 'dynamic/logs')):
    os.mkdir(os.path.join(ROOT, 'dynamic/logs'))

client = zhihu.ZhihuClient(test_cookie)


class EndProgramException(Exception):
    pass


class InvalidTopicId(Exception):
    pass


class LackConfig(Exception):
    pass

class NoSuchActivity(Exception):
    pass

class FetchTypeError(Exception):
    pass