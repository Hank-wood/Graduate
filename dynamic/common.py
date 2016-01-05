import os

# zhihu-analusis
ROOT = os.path.dirname(os.path.dirname(__file__))
test_cookie = os.path.join(ROOT, 'cookies/zhuoyi.json')
dynamic_config_file = os.path.join(ROOT, 'dynamic/config/dynamic_config.json')
logging_config_file = os.path.join(ROOT, 'dynamic/config/logging_config.json')
TOPIC_PREFIX = "https://www.zhihu.com/topic/"
QUESTION_PREFIX = "https://www.zhihu.com/question/"

if not os.path.exists(os.path.join(ROOT, 'dynamic/logs')):
    os.mkdir(os.path.join(ROOT, 'dynamic/logs'))


class EndProgramException(Exception):
    pass


class InvalidTopicId(Exception):
    pass


class LackConfig(Exception):
    pass