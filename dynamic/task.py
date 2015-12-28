# coding: utf-8

"""
定义任务类
"""

import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from utils import *
from utils import task_queue

logger = logging.getLogger(__name__)


class Task:

    executor = ThreadPoolExecutor(max_workers=4)


class FetchNewAnswer(Task):
    def __init__(self, question):
        self.question = question

    def execute(self):
        logger.debug("%s Fetch answer from: %s" %
              (now_string(), self.question.title))
        task_queue.append(FetchNewAnswer(self.question))


class FetchAnswerInfo(Task):
    pass


__all__ = [
    'FetchNewAnswer',
    'FetchAnswerInfo'
]