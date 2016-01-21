# coding: utf-8

"""
定义任务类
"""

import logging
from datetime import datetime
from collections import deque, OrderedDict
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util import Retry

from zhihu.acttype import ActType

from utils import *
from common import *
from model import QuestionManager, AnswerManager

logger = logging.getLogger(__name__)


class FetchNewAnswer():
    def __init__(self, tid, question, answer_num=0, from_db=False):
        """
        :param question: zhihu.Question object
        :return:
        """
        self.tid = tid
        self.question = question

        if self.question.deleted:
            QuestionManager.remove_question(self.tid, self.question.id)
            return

        self.answer_num = answer_num
        self.aids = set()
        if not from_db:
            logger.info("New Question: %s" % self.question.title)

    def execute(self):
        self.question.refresh()

        if self.question.deleted:
            QuestionManager.remove_question(self.tid, self.question.id)
            return

        if self.question.answer_num > self.answer_num:
            # We can't just fetch the latest
            # question.answer_num - self.answer answers, cause there exist
            # collapsed answers
            # 当然这里可能还是有问题,比如答案被折叠导致 question.answer_num 不增
            # 但实际上是有新答案的
            for answer in self.question.answers:
                if str(answer.id) not in self.aids:
                    if len(self.aids) == 0:
                        # a new connection pool for question that has answer
                        prefix = self.question.url[:-1]  # question/1234, remove trailing slash
                        self.question._session.mount(prefix,
                                HTTPAdapter(pool_connections=1,
                                            pool_maxsize=100,
                                            max_retries=Retry(100)))
                    self.aids.add(str(answer.id))
                    task_queue.append(FetchAnswerInfo(self.tid, answer))
                else:
                    break

            self.answer_num = self.question.answer_num

        task_queue.append(self)


class FetchAnswerInfo():
    def __init__(self, tid, answer):
        self.tid = tid
        self.answer = answer
        self.manager = AnswerManager(tid, str(answer.id))
        self.manager.sync_basic_info(
                qid=answer.question.id, url=answer.url,
                answerer=answer.author.id, time=answer.creation_time)

    def execute(self):
        logger.info("Fetch answer info: %s - %s" % (self.answer.author.name,
                                                    self.answer.question.title))
        new_upvoters = deque()
        new_commenters = OrderedDict()
        new_collectors = []
        self.answer.refresh()

        if self.answer.deleted:
            logger.info("Answer deleted %s - %s" % (self.answer.id,
                                                    self.answer.question.title))
            self.manager.remove_answer()
            return

        # Note: put older event in lower index

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
        # 注意, 一次新增的评论中也会有同一个人发表多条评论的情况, 需要收集最早的那个
        # 下面的逻辑保证了同一个 commenter 的更早的 comment 会替代新的
        for comment in reversed(list(self.answer.comments)):
            if comment.author.id in self.manager.commenters:
                if comment.creation_time <= self.manager.lastest_comment_time:
                    break
            else:
                new_commenters[comment.author.id] = {
                    'uid': comment.author.id,
                    'time': comment.creation_time,
                    'cid': comment.cid
                }

        new_commenters = list(reversed(new_commenters.values()))

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

        new_collectors.sort(key=lambda x: x['time'])

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
            if act.type == ActType.UPVOTE_ANSWER:
                if act.content.url == answer.url:
                    return act.time
            if i > 10:
                logger.error("Can't find upvote activity")
                raise NoSuchActivity

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