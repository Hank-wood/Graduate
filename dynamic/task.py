# coding: utf-8

"""
定义任务类
"""

import logging
from datetime import datetime
from collections import deque, OrderedDict
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
# from requests.packages.urllib3.util import Retry

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
        self.continue_task = True  # 是否继续执行 task
        if question:
            self.question = question
            self.qid = str(question.id)

            if self.question.deleted:
                self._delete_question('Question deleted:' + self.qid)
                return

            self.asker = question.author.id if question.author is not ANONYMOUS else ''
            self.answer_num = 0
            self.follower_num = 1  # 初始提问者
            self.last_update_time = datetime.now()  # 最后一次增加新答案的时间
            logger.info("New Question %s: %s" % (self.qid, self.question.title))
        elif question_doc:
            self.question = get_client().question(question_doc['url'])
            self.qid = str(self.question.id)
            self.answer_num = 0

            if self.question.deleted:
                self._delete_question('Question deleted:' + self.qid)
                return

            self.asker = question_doc['asker']
            self.last_update_time = epoch  # 最后一次增加新答案的时间
            for url, ctime in AnswerManager.get_question_answer_attrs(
                            self.tid, self.qid, 'url', 'time'):
                self.answer_num += 1
                answer_task_queue.append(FetchAnswerInfo(self.tid, url=url))
                if ctime > self.last_update_time:
                    self.last_update_time = ctime

            if self.answer_num > 0:
                self._mount_pool()  # 已经有答案
            else:
                # 数据库中的问题没有答案, 删除
                self._delete_question("Remove 0 answer question: " + self.qid)
                return

            self.follower_num = QuestionManager.get_question_follower_num(self.tid, self.qid)
        else:
            raise Exception("FetchQuestionInfo needs question or question_doc")

    def execute(self):
        if self.continue_task:
            question_task_queue.append(self)
        else:
            return

        self.question.refresh()

        if self.question.deleted:
            self._delete_question('Question deleted:' + self.qid)
            return

        answer_num_old = self.answer_num
        if self.question.answer_num > self.answer_num:
            # We can't just fetch the latest new_answer_num - old_answer_num
            # answers, cause there exist collapsed answers
            # 当然这里可能还是有问题,比如答案被折叠导致 question.answer_num 不增
            # 但实际上是有新答案的。暂时忽略。
            for i, answer in enumerate(self.question.answers):
                if answer.creation_time > self.last_update_time:
                    if i == 0:
                        latest_answer = answer
                    if self.answer_num == 0:
                        # a new connection pool for question that has answer
                        # remove trailing slash so ?sort can use this pool
                        # 答案的url 是 question/qid/answer/aid
                        self._mount_pool()
                    answer_task_queue.append(FetchAnswerInfo(self.tid, answer))
                    self.answer_num += 1
                else:
                    break

        if self.answer_num > answer_num_old:
            self.last_update_time = latest_answer.creation_time
            if self.question.follower_num > self.follower_num:
                huey_tasks.fetch_question_follower(self.tid, self.qid, self.asker)
                # 注意 follower_num 多于数据库中的 follower, 只有纯follower会入库
                self.follower_num = self.question.follower_num

        self._check_question_activation()

    def _check_question_activation(self):
        active_interval = datetime.now() - self.last_update_time
        if self.answer_num == 0 and active_interval > MAX_NO_ANSWER_INTERVAL:
            # x min 没有回答，删除问题
            self._delete_question("Remove 0 answer question: " + self.qid)
            return False
        elif active_interval > QUESTION_INACTIVE_INTERVAL:
            # 已有答案的问题不从数据库删除, 仅移除 task
            self.continue_task = False
            QuestionManager.set_question_inactive(self.tid, self.qid)
            logger.info("Cancel inactive question task: " + self.qid)
            return False
        else:
            return True

    def _delete_question(self, msg=''):
        self.continue_task = False
        logger.info(msg)
        QuestionManager.remove_question(self.tid, self.qid)
        # try:
        #     del self.question._session.adapters[self.question.url[:-1]]
        # except KeyError:
        #     pass

    def _mount_pool(self):
        self.question._session.mount(self.question.url[:-1],
                                     HTTPAdapter(pool_connections=1,
                                                 pool_maxsize=10))


class FetchAnswerInfo():
    def __init__(self, tid, answer=None, url=None):
        self.tid = tid
        self.continue_task = True  # 是否继续执行 task
        if answer:
            self.answer = answer
            if answer.url.startswith('https'):
                answer._url = 'http' + answer.url[5:]  #为了能够使用代理,走httpx
            self.aid = str(answer.id)
            self.manager = AnswerManager(tid, self.aid)
            answerer = '' if answer.author is ANONYMOUS else answer.author.id
            if self.manager.answer_exists(tid, self.aid):
                logger.warning("answer exists: " + answer.url)
                return
            self.manager.save_answer(qid=answer.question.id,
                                     url=answer.url,
                                     answerer=answerer,
                                     time=answer.creation_time)
            self.last_update_time = answer.creation_time  # 最后一次增加新upvote的时间
            self.upvote_num = self.comment_num = self.collect_num = 0
            logger.info("New answer: %s - %s" % (self.answer.author.name,
                                                 self.answer.question.title))
        elif url:
            # 已经存在于数据库中的答案
            self.answer = get_client().answer(url)
            self.aid = str(self.answer.id)
            self.manager = AnswerManager(tid, self.aid)
            self.last_update_time = self.manager.lastest_upvote_time
            # 这里的 comment_num 是 commenter_num, 实际可能更多
            self.upvote_num, self.comment_num, self.collect_num = \
                self.manager.get_answer_affecter_num(tid, self.aid)

    def _check_answer_activation(self):
        active_interval = datetime.now() - self.last_update_time
        if active_interval > ANSWER_INACTIVE_INTERVAL:
            self.continue_task = False
            logger.info("Cancel inactive answer task %s - %s" %
                        (self.answer.id, self.answer.question.title))
            return False  # 3h没有新upvote
        else:
            return True

    def _delete_answer(self):
        self.continue_task = False
        logger.info("Answer deleted %s - %s" % (self.answer.id,
                                                self.answer.question.title))
        self.manager.remove_answer()

    def execute(self):
        # 保证不会因为下面卡住导致task 不加入queue
        if self.continue_task:
            answer_task_queue.append(self)
        else:
            return

        new_upvoters = deque()
        new_commenters = OrderedDict()
        new_collectors = []
        self.answer.refresh()

        if self.answer.deleted:
            self._delete_answer()
            return

        # Note: put older event in lower index

        # add upvoters, 匿名用户不记录
        if self.answer.upvote_num > self.upvote_num:
            self.upvote_num = self.answer.upvote_num
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
                self.last_update_time = new_upvoters[-1]['time']

        if not self._check_answer_activation():
            return  # 不删除回答!!

        # add commenters, 匿名用户不记录
        # 同一个人可能发表多条评论, 所以还得 check 不是同一个 commenter
        # 注意, 一次新增的评论中也会有同一个人发表多条评论的情况, 需要收集最早的那个
        # 下面的逻辑保证了同一个 commenter 的更早的 comment 会替代新的
        if self.answer.comment_num > self.comment_num:
            self.comment_num = self.answer.comment_num
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
            if new_commenters:
                new_commenters = list(reversed(new_commenters.values()))

        # add collectors
        # 收藏夹不是按时间返回, 所以只能全部扫一遍
        if self.answer.collect_num > self.collect_num:
            self.collect_num = self.answer.collect_num
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