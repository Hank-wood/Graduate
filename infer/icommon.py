import os
import json
import sys
import logging
import logging.config
from collections import namedtuple
from enum import Enum

from pymongo import MongoClient

ASK_QUESTION = 0b000001
FOLLOW_QUESTION = 0b000010
ANSWER_QUESTION = 0b000100
UPVOTE_ANSWER = 0b001000
COMMENT_ANSWER = 0b010000
COLLECT_ANSWER = 0b100000

action_table = {
    0b000001: 'ASK_QUESTION',
    0b000010: 'FOLLOW_QUESTION',
    0b000100: 'ANSWER_QUESTION',
    0b001000: 'UPVOTE_ANSWER',
    0b010000: 'COMMENT_ANSWER',
    0b100000: 'COLLECT_ANSWER',
}

ROOT = os.path.dirname(os.path.dirname(__file__))

db = MongoClient('127.0.0.1', 27017).zhihu_data
logging_config_file = os.path.join(ROOT, 'infer/config/logging_config.json')
smtp_config_file = os.path.join(ROOT, 'dynamic/config/smtp_config.json')

if not os.path.exists(os.path.join(ROOT, 'infer/logs')):
    os.mkdir(os.path.join(ROOT, 'infer/logs'))
logging_dir = os.path.join(ROOT, 'infer/logs')

if os.path.isfile(logging_config_file):
    with open(logging_config_file, 'rt') as f:
        config = json.load(f)
        logging.config.dictConfig(config)

logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
sys.modules[__name__].__dict__['logger'] = logger

smtp_handler = logging.getLogger().handlers[2]
assert isinstance(smtp_handler, logging.handlers.SMTPHandler)
if 'mailgun_username' in os.environ:
    smtp_handler.username, smtp_handler.password = \
        os.environ['mailgun_username'], os.environ['mailgun_password']
else:
    with open(smtp_config_file, 'rt') as f:
        smtp_config = json.load(f)
        smtp_handler.username, smtp_handler.password = \
            smtp_config['username'], smtp_config['password']

UserAction = namedtuple('UserAction', ['time', 'aid', 'uid', 'acttype'])
Relation = namedtuple('Relation', ['head', 'tail', 'reltype'])


class RelationType(Enum):
    follow = 1
    qlink = 2
    notification = 3
    recommendation = 4

    def __str__(self):
        if self.value == 1:
            return 'follow'
        elif self.value == 2:
            return 'qlink'
        elif self.value == 3:
            return 'notification'
        else:
            return 'recommendation'


class FetchTypeError(Exception):
    pass