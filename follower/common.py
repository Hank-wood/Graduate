import os


# zhihu-analysis folder
ROOT = os.path.dirname(os.path.dirname(__file__))
test_cookie = os.path.join(ROOT, 'cookies/zhuoyi.json')
logging_config_file = os.path.join(ROOT, 'follower/config/logging_config.json')
TOPIC_PREFIX = "https://www.zhihu.com/topic/"
QUESTION_PREFIX = "https://www.zhihu.com/question/"

if not os.path.exists(os.path.join(ROOT, 'follower/logs')):
    os.makedirs(os.path.join(ROOT, 'follower/logs'), exist_ok=True)
