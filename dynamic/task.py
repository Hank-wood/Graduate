# coding: utf-8

"""
定义任务类
"""

import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from zhihu import acttype

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

    @staticmethod
    def get_upvote_time(upvoter, answer):
        """
        :param upvoter: zhihu.Author
        :param answer: zhihu.Answer
        :return: datatime.datetime
        """
        for i, act in enumerate(upvoter.activities):
            if act.type == acttype.UPVOTE_ANSWER:
                if act.content.url == answer.url:
                    return act.time
            if i > 10:
                logger.error("Can't find upvote activity")
                raise NoSuchActivity

    @staticmethod
    def get_comment_time(comment):
        """
        :param answer: zhihu.Comment
        :return: datatime.datetime
        """
        time_string = comment.time_string

        if ':' in time_string:  # hour:minute, 19:58
            return get_datetime_hour_min_sec(time_string + ':00')
        else:  # year-month-day, 2016-01-04. Shouldn't be here
            logger.warning('comment time_string: ' + time_string)
            return get_datetime_day_month_year(time_string)

    @staticmethod
    def get_collector_time(collector, collection):
        """
        :param collector: zhihu.Author
        :param answer: zhihu.Answer
        :return: datatime.datetime
        """
        pass

__all__ = [
    'FetchNewAnswer',
    'FetchAnswerInfo'
]