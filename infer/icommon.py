import os
import json
import sys
import logging
import logging.config
from collections import namedtuple
from enum import Enum
from datetime import datetime
from typing import Union

from pymongo import MongoClient

ASK_QUESTION = 0b000001
FOLLOW_QUESTION = 0b000010
ANSWER_QUESTION = 0b000100
UPVOTE_ANSWER = 0b001000
COMMENT_ANSWER = 0b010000
COLLECT_ANSWER = 0b100000

USER_PREFIX = 'https://www.zhihu.com/people/'
action_table = {
    0b000001: 'ASK_QUESTION',
    0b000010: 'FOLLOW_QUESTION',
    0b000100: 'ANSWER_QUESTION',
    0b001000: 'UPVOTE_ANSWER',
    0b010000: 'COMMENT_ANSWER',
    0b100000: 'COLLECT_ANSWER',
}

ROOT = os.path.dirname(os.path.dirname(__file__))

if hasattr(os, '_called_from_test'):
    db2 = MongoClient('127.0.0.1', 27017, connect=False).test
else:
    db2 = MongoClient('127.0.0.1', 27017, connect=False).analysis
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


class UserAction:
    def __init__(self, time, aid, uid, acttype):
        self.time = time
        self.aid = aid
        self.uid = uid
        self.acttype = acttype

    def __lt__(self, other):
        return self.time < other.time

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        for key in self.__dict__:
            assert self.__dict__[key] == other.__dict__[key]
        return self.__dict__ == other.__dict__

Relation = namedtuple('Relation', ['head', 'tail', 'reltype'])


class FollowEdge:
    def __init__(self, head, tail):
        self.head = head
        self.tail = tail

    def __eq__(self, other):
        return self.head == other.head and self.tail == other.tail

    def __hash__(self):
        return hash(self.head.uid + self.tail.uid)

    def __repr__(self):
        return self.head.uid + ',' + self.tail.uid


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

match = {
    'follow': RelationType.follow,
    'qlink': RelationType.qlink,
    'notification': RelationType.notification,
    'recommendation': RelationType.recommendation
}


class FetchTypeError(Exception):
    pass


class TimeRange:
    def __init__(self, start=None, end=None):
        self.start = start
        self.end = end

    def __eq__(self, other):
        return self.start == other.start and self.end == other.end

    def __str__(self):
        return "(%s,%s)" % (self.start, self.end)

    def __le__(self, other):
        return self - other <= 0

    def __gt__(self, other):
        return not self.__le__(other)

    def dump(self):
        return self.__dict__


def sub(self, other: Union[datetime, TimeRange]):
    """
    用来判断时间相对顺序
    :return:
        -1 if self <= other;
        1 if self >= other;
        0 if unknown
    """
    if isinstance(other, datetime):
        if self.start and self.start >= other:
            return 1  # self > other
        elif self.end and self.end <= other:
            return -1  # self < other
        else:
            return 0  # unknown
    else:
        # TimeRange
        if self.end and other.start and self.end <= other.start:
            return -1
        elif self.start and other.end and self.start >= other.end:
            return 1
        else:
            return 0

TimeRange.__sub__ = sub
