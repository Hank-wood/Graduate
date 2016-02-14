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

from utils import *
from common import *
from manager import QuestionManager, AnswerManager
from client_pool import get_client
import huey_tasks

logger = logging.getLogger(__name__)


class FetchQuestionInfo():
    def __init__(self, tid, question=None, question_doc=None):
        """
        :param question: zhihu.Question object
        :return:
        """
        self.tid = tid
        self.aids = set()
        if question:
            self.question = question
            self.qid = str(question.id)

            if self.question.deleted:
                self._delete_question()
                return

            self.asker = question.author.id if question.author is not ANONYMOUS else ''
            self.follower_num = 0
            self.last_update_time = datetime.now()  # 最后一次增加新答案的时间
            logger.info("New Question %s: %s" % (self.qid, self.question.title))
        elif question_doc:
            self.question = get_client().question(question_doc['url'])
            self.qid = str(self.question.id)

            if self.question.deleted:
                self._delete_question()
                return

            self.asker = question_doc['asker']
            self.last_update_time = datetime(1970, 1, 1)  # 最后一次增加新答案的时间
            for aid, url, ctime in AnswerManager.get_question_answer_attrs(
                            self.tid, self.qid, 'aid', 'url', 'time'):
                self.aids.add(aid)
                task_queue.append(FetchAnswerInfo(self.tid, url=url))
                if ctime > self.last_update_time:
                    self.last_update_time = ctime

            if len(self.aids) > 0:
                self._mount_pool()  # 已经有答案
            else:
                self._delete_question()  # 数据库中的问题没有答案, 删除
                return

            self.follower_num = QuestionManager.get_question_follower_num(self.tid, self.qid)
        else:
            raise Exception("FetchQuestionInfo needs question or question_doc")

    def execute(self):
        self.question.refresh()

        if self.question.deleted:
            self._delete_question()
            return

        # TODO: 或许可以用id 来判断先后,不需要set
        answer_count = len(self.aids)
        if self.question.answer_num > len(self.aids):
            # We can't just fetch the latest new_answer_num - old_answer_num
            # answers, cause there exist collapsed answers
            # 当然这里可能还是有问题,比如答案被折叠导致 question.answer_num 不增
            # 但实际上是有新答案的。暂时忽略。
            for answer in self.question.answers:
                if str(answer.id) not in self.aids:
                    if len(self.aids) == 0:
                        # a new connection pool for question that has answer
                        # remove trailing slash so ?sort can use this pool
                        # 答案的url 是 question/qid/answer/aid
                        self._mount_pool()
                    self.aids.add(str(answer.id))
                    task_queue.append(FetchAnswerInfo(self.tid, answer))
                else:
                    break

        if len(self.aids) > answer_count:
            self.last_update_time = datetime.now()

        if not self._check_question_activation():
            self.cancel_task()
            return

        if self.question.follower_num > self.follower_num:
            self._fetch_question_follower()
            # 注意 follower_num 多于数据库中的 follower, 只有纯follower会入库
            self.follower_num = self.question.follower_num

        task_queue.append(self)

    def _check_question_activation(self):
        active_interval = datetime.now() - self.last_update_time
        if len(self.aids) == 0 and active_interval > MAX_NO_ANSWER_INTERVAL:
            return False  # 15min没有回答，删除问题
        elif active_interval > QUESTION_INACTIVE_INTERVAL:
            return False  # 3h没有新回答，删除问题
        else:
            return True

    # TODO: delete question 可以用huey 执行
    def _delete_question(self):
        logger.info("Remove 0 answer question: " + self.qid)
        QuestionManager.remove_question(self.tid, self.qid)
        try:
            del self.question._session.adapters[self.question.url[:-1]]
        except KeyError:
            pass

    def cancel_task(self):
        """已有答案的问题不从数据库删除, 仅移除 task"""
        logger.info("Cancel inactive question task: " + self.qid)
        try:
            del self.question._session.adapters[self.question.url[:-1]]
        except KeyError:
            pass

    def _mount_pool(self):
        self.question._session.mount(self.question.url[:-1],
                                     HTTPAdapter(pool_connections=1,
                                                 pool_maxsize=100,
                                                 max_retries=Retry(10)))
    # TODO: 可以用 Huey
    def _fetch_question_follower(self):
        # 如果是关注问题或回答问题的人就不抓, 因为关注问题事件不会出现在activities
        # 回答者 id 从数据库里取，因为在初始化 FetchAnswerInfo 的时候就入库了
        answerers = AnswerManager.get_question_answerer(self.tid, self.qid)
        answerers.add(self.asker)
        old_followers = QuestionManager.get_question_follower(self.tid,self.qid,
                                                              limit=5)
        new_followers = []
        now = datetime.now()

        # 这里直接采取最简单的逻辑,因为不太会有人取关又关注
        r = range(20)  # 20个刚好只需要一次请求
        for follower in self.question.followers:
            if follower is ANONYMOUS:
                continue
            if follower.id in old_followers:
                break
            elif follower.id not in answerers:
                huey_tasks.fetch_followers_followees(follower.id, now)
                for _, act in zip(r, follower.activities):
                    if act.type == FOLLOW_QUESTION and str(act.content.id) == self.qid:
                        new_followers.append({
                            'uid': follower.id,
                            'time': act.time
                        })
                        break
                else:
                    logger.warning("Can't find follow question activity")
                    logger.warning("question: %s, follower: %s" % (self.qid, follower.id))
                    # 没有具体时间，就不记录。因为follower有序，时间可之后推定。
                    new_followers.append({
                        'uid': follower.id,
                        'time': None
                    })

        QuestionManager.add_question_follower(self.tid, self.qid, new_followers)


class FetchAnswerInfo():
    def __init__(self, tid, answer=None, url=None):
        self.tid = tid
        if answer:
            self.answer = answer
            self.manager = AnswerManager(tid, answer.id)
            answerer = '' if answer.author is ANONYMOUS else answer.author.id
            self.manager.save_answer(qid=answer.question.id,
                                     url=answer.url,
                                     answerer=answerer,
                                     time=answer.creation_time)
            self.last_update_time = datetime.now()  # 最后一次增加新upvote的时间
            logger.info("New answer: %s - %s" % (self.answer.author.name,
                                                 self.answer.question.title))
        elif url:
            # 已经存在于数据库中的答案
            self.answer = get_client().answer(url)
            self.manager = AnswerManager(tid, self.answer.id)
            self.last_update_time = self.manager.lastest_upvote_time

    def _check_answer_activation(self):
        active_interval = datetime.now() - self.last_update_time
        if active_interval > ANSWER_INACTIVE_INTERVAL:
            return False  # 3h没有新upvote，删除回答
        else:
            return True

    def _delete_answer(self):
        logger.info("Answer deleted %s - %s" % (self.answer.id,
                                                self.answer.question.title))
        self.manager.remove_answer()

    def execute(self):
        new_upvoters = deque()
        new_commenters = OrderedDict()
        new_collectors = []
        self.answer.refresh()

        if self.answer.deleted:
            self._delete_answer()
            return

        # Note: put older event in lower index

        # add upvoters, 匿名用户不记录
        for upvoter in self.answer.upvoters:
            if upvoter is ANONYMOUS:
                continue
            if upvoter.id in self.manager.upvoters:
                break
            else:
                new_upvoters.appendleft({
                    'uid': upvoter.id,
                    'time': self.get_upvote_time(upvoter, self.answer)
                })

        if new_upvoters:
            self.last_update_time = datetime.now()

        if not self._check_answer_activation():
            logger.info("Cancel inactive answer task %s - %s" % (self.answer.id,
                                                self.answer.question.title))
            return  # 不删除回答!!

        # add commenters, 匿名用户不记录
        # 同一个人可能发表多条评论, 所以还得 check 不是同一个 commenter
        # 注意, 一次新增的评论中也会有同一个人发表多条评论的情况, 需要收集最早的那个
        # 下面的逻辑保证了同一个 commenter 的更早的 comment 会替代新的
        for comment in self.answer.latest_comments:
            if comment.author is ANONYMOUS:
                continue
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
        for i, act in enumerate(upvoter.activities, 1):
            if act.type == ActType.UPVOTE_ANSWER:
                if act.content.url == answer.url:
                    return act.time
            if i >= 20:
                logger.warning("Can't find upvote activity")
                logger.warning("%s upvotes %s" % (upvoter.id, answer.url))
                return None

    @staticmethod
    def get_collect_time(answer, collection):
        """
        :param answer: zhihu.Answer
        :param collection: zhihu.Collection
        :return: datatime.datetime
        """
        for i, log in enumerate(collection.logs, 1):
            if log.answer is None:  # create collection
                break
            if answer.url == log.answer.url:
                return log.time
            if i >= 20:
                break

        logger.warning("Can't find collect activity")
        logger.warning("%s collects %s" % (collection.owner.id, answer.url))
        return None

__all__ = [
    'FetchQuestionInfo',
    'FetchAnswerInfo'
]