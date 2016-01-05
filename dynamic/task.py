# coding: utf-8

"""
定义任务类
"""

import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from utils import *
from utils import task_queue
from model import AnswerModel

logger = logging.getLogger(__name__)


class Task:

    executor = ThreadPoolExecutor(max_workers=4)


class FetchNewAnswer(Task):
    def __init__(self, tid, question, answer_num=0):
        """
        :param question: zhihu.Question object
        :return:
        """
        self.tid = tid
        self.question = question
        self.answer_num = answer_num
        self.aids = set()

    def execute(self):
        logger.debug("Fetch answer from: %s" % self.question.title)

        if self.question.answer_num <= self.answer_num:
            pass
        else:
            self.question.refresh()
            if self.question.answer_num > self.answer_num:
                # We can't just fetch the latest
                # question.answer_num - self.answer answers, cause there exist
                # collapsed answers
                for answer in self.question.answers:
                    if str(answer.id) not in self.aids:
                        self.aids.add(str(answer.id))
                        task_queue.append(FetchAnswerInfo(tid, answer))
                    else:
                        break

                self.answer_num = self.question.answer_num

        task_queue.append(self)


class FetchAnswerInfo(Task):
    def __init__(self, tid, answer):
        self.tid = tid
        self.answer = answer
        self.answer_model = AnswerModel(self.tid, answer=answer)
        self.answer_model.save()

    def execute(self):
        new_upvoters = []
        new_commenters = []
        new_collectors = []
        self.answer.refresh()

        for upvoter in self.answer.upvoters:
            lastest_upvoter_id = self.answer_model.upvoters[-1]['uid']
            lastest_upvote_time = self.answer_model.upvoters[-1]['time']

            if upvoter.id == lastest_upvoter_id:
                break
            # TODO, 实现逻辑
            upvote_time = get_upvote_time(upvoter, answer)
            if upvote_time <= lastest_upvote_time:
                break
            else:
                new_upvoters.append({'uid': upvoter.id, 'time': upvote_time})

        # TODO: same with the other two

        self.answer_model.update(new_upvoters, new_commenters, new_collectors)
        task_queue.append(self)



__all__ = [
    'FetchNewAnswer',
    'FetchAnswerInfo'
]