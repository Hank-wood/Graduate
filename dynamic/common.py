import os

# zhihu-analusis
ROOT = os.path.dirname(os.path.dirname(__file__))
test_cookie = os.path.join(ROOT, 'cookies/zhuoyi.json')
dynamic_config_file = os.path.join(ROOT, 'dynamic/config/dynamic_config.json')
logging_config_file = os.path.join(ROOT, 'dynamic/config/logging_config.json')


class EndProgramException(Exception):
    pass


class InvalidTopicId(Exception):
    pass


class LackConfig(Exception):
    pass