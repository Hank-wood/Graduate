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

        # add upvoters
        for upvoter in self.answer.upvoters:
            if upvoter.id in self.answer_model.upvoters:
                break
            else:
                new_upvoters.append({
                    'uid': upvoter.id,
                    'time': self.get_upvote_time(upvoter, self.answer)
                })

        # add commenters
        for comment in reversed(list(self.answer.comments)):
            if comment.cid in self.answer_model.comments:
                break
            elif comment.author.id not in self.answer_model.commenters:
                new_commenters.append({
                    'uid': comment.author.id,
                    'time': self.get_comment_time(comment)
                })

        # add collectors
        # 收藏夹不是按时间返回, 所以只能全部扫一遍
        if self.answer.collect_num > len(self.answer_model.collections):
            for collection in self.answer.collections:
                if collection.id not in self.answer_model.collections:
                    new_collectors.append({
                        'uid': collection.owner.id,
                        'time': self.get_collect_time(self.answer, collection)
                    })

        # TODO: also update comment_id, collection_id
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
        :param comment: zhihu.Comment
        :return: datatime.datetime
        """
        time_string = comment.time_string

        if ':' in time_string:  # hour:minute, 19:58
            return get_datetime_hour_min_sec(time_string + ':00')
        else:  # year-month-day, 2016-01-04. Shouldn't be here
            logger.warning('comment time_string: ' + time_string)
            return get_datetime_day_month_year(time_string)

    @staticmethod
    def get_collect_time(answer, collection):
        """
        :param answer: zhihu.Answer
        :param collection: zhihu.Collection
        :return: datatime.datetime
        """
        for log in collection.logs:
            if log.answer is None:  # create collection
                continue
            if answer.url == log.answer.url:
                return log.time
        else:
            logger.error("Can't find collect activity")
            raise NoSuchActivity

__all__ = [
    'FetchNewAnswer',
    'FetchAnswerInfo'
]