# coding: utf-8

"""
定义任务类
"""

import logging
from datetime import datetime
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from zhihu import acttype

from utils import *
from model import AnswerManager

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
        self.manager = AnswerManager(tid, answer.aid)
        self.manager.sync_basic_info(
                qid=answer.question.id, url=answer.url,
                answerer=answer.author.id, time=answer.time)

    def execute(self):
        new_upvoters = deque()
        new_commenters = deque()
        new_collectors = deque()
        self.answer.refresh()

        # Note: put older event in lower index, use appendleft

        # add upvoters
        for upvoter in self.answer.upvoters:
            if upvoter.id in self.manager.upvoters:
                break
            else:
                new_upvoters.appendleft({
                    'uid': upvoter.id,
                    'time': self.get_upvote_time(upvoter, self.answer)
                })

        # add commenters
        # 同一个人可能发表多条评论, 所以还得 check 不是同一个 commenter
        for comment in reversed(list(self.answer.comments)):
            if comment.author.id in self.manager.commenters:
                if comment.time <= self.manager.lastest_comment_time:
                    break
            else:
                new_commenters.appendleft({
                    'uid': comment.author.id,
                    'time': self.get_comment_time(comment),
                    'cid': comment.cid
                })

        # add collectors
        # 收藏夹不是按时间返回, 所以只能全部扫一遍
        if self.answer.collect_num > len(self.manager.collectors):
            for collection in self.answer.collections:
                if collection.owner.id not in self.manager.collectors:
                    new_collectors.append({
                        'uid': collection.owner.id,
                        'time': self.get_collect_time(self.answer, collection),
                        'cid': collection.id
                    })

        self.manager.sync_affected_users(new_upvoters=new_upvoters,
                                         new_commenters=new_commenters,
                                         new_collectors=new_collectors)
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