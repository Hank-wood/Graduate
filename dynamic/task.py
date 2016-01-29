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
from manager import QuestionManager, AnswerManager
import huey_tasks

logger = logging.getLogger(__name__)


class FetchQuestionInfo():
    def __init__(self, tid, question, from_db=False):
        """
        :param question: zhihu.Question object
        :return:
        """
        self.tid = tid
        self.question = question
        self.qid = question.id
        self.asker = question.author.id

        if self.question.deleted:
            QuestionManager.remove_question(self.tid, self.qid)
            return

        # TODO: 从数据库中获得该question 的已有 answer,添加 FetchAnswerInfo 任务
        self.answer_num = 0
        # TODO: 从数据库中获得follower_num, answer_num
        self.follower_num = self.question.follower_num
        self.aids = set()
        if not from_db:
            logger.info("New Question: %s" % self.question.title)

    def execute(self):
        self.question.refresh()

        if self.question.deleted:
            QuestionManager.remove_question(self.tid, self.qid)
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
                        # remove trailing slash so ?sort can use this pool
                        # 答案的url 是 question/qid/answer/aid
                        prefix = self.question.url[:-1]
                        self.question._session.mount(prefix,
                                HTTPAdapter(pool_connections=1,
                                            pool_maxsize=100,
                                            max_retries=Retry(100)))
                    self.aids.add(str(answer.id))
                    task_queue.append(FetchAnswerInfo(self.tid, answer))
                else:
                    break
            self.answer_num = self.question.answer_num

        if self.question.follower_num > self.follower_num:
            self._fetch_question_follower()
            # 注意 follower_num 多于数据库中的 follower, 只有纯follower会入库
            self.follower_num = self.question.follower_num

        task_queue.append(self)

    def _fetch_question_follower(self):
        # 如果是关注问题或回答问题的人就不抓, 因为关注问题事件不会出现在activities
        # 回答者 id 从数据库里取，因为在初始化 FetchAnswerInfo 的时候就入库了
        answerers = AnswerManager.get_question_answerer(self.tid, self.qid)
        answerers.add(self.asker)
        # TODO: old follower 不要全部取出,只取最新的几个就行.节省内存
        old_followers = QuestionManager.get_question_follower(self.tid,self.qid)
        new_followers = []

        # 这里直接采取最简单的逻辑,因为不太会有人取关又关注
        for follower in self.question.followers:
            if follower.id in old_followers:
                break
            elif follower.id not in answerers:
                for i, act in enumerate(follower.activities):
                    if act.type == ActType.FOLLOW_QUESTION and \
                    act.content.id == self.qid:
                        new_followers.append({
                            'uid': follower.id,
                            'time': act.time
                        })
                        huey_tasks.fetch_followers_followees(follower.id,
                                                             datetime.now())
                    if i > 10:
                        logger.warning("Can't find follow question activity")
                        break

        QuestionManager.add_question_follower(self.tid, self.qid, new_followers)


class FetchAnswerInfo():
    def __init__(self, tid, answer=None, url=None):
        self.tid = tid
        if answer:
            self.answer = answer
            self.manager = AnswerManager(tid, answer.id)
            self.manager.save_answer(qid=answer.question.id,
                                     url=answer.url,
                                     answerer=answer.author.id,
                                     time=answer.creation_time)
        elif url:
            self.answer = client.answer(url)
            self.manager = AnswerManager(tid, self.answer.id)

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
        for comment in self.answer.latest_comments:
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
    'FetchQuestionInfo',
    'FetchAnswerInfo'
]