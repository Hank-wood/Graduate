# coding: utf-8

"""
定期爬话题页面
"""

import logging
from concurrent.futures import ThreadPoolExecutor

import requests
from zhihu.question import Question

from task import *
from manager import QuestionManager
from utils import task_queue
from common import *
from client_pool import get_client

logger = logging.getLogger(__name__)


class TopicMonitor:

    def __init__(self):
        self.client = get_client()
        self.topics = [
            self.client.topic(TOPIC_PREFIX + tid) for tid in topics
        ]
        if fetch_old:
            self._load_old_question()
        self.executor = ThreadPoolExecutor(max_workers=len(topics))

    def _load_old_question(self):
        # 数据库中已有的 question 加入 task queue, answer 不用管
        logger.info('Loading old questions from database............')

        for question_doc in QuestionManager.get_all_questions('url', 'topic', 'asker'):
            if question_doc['url'].endswith('/'):
                question_doc['url'] = question_doc['url'][:-1] + '?sort=created'
            task_queue.append(FetchQuestionInfo(tid=question_doc['topic'],
                                                question_doc=question_doc))

        logger.info('Loading old questions from database succeed :)')

    def detect_new_question(self):
        """
        爬取话题页面，寻找新问题
        """
        for topic in self.topics:
            self.executor.submit(self.execute, topic)
            # self.execute(topic)

    def execute(self, topic):
        tid = str(topic.id)
        it = iter(topic.questions)
        question = next(it)
        latest_ctime = QuestionManager.latest_question_creation_time[tid]
        QuestionManager.set_latest(tid, question.creation_time)

        # latest_ctime is None 代表第一次执行, 此时不抓取新问题
        if latest_ctime is None:
            return

        while question.creation_time > latest_ctime:
            question._url = question.url[:-1] + '?sort=created'
            try:
                if question.deleted:
                    continue
                # 去掉占了多个所选话题的问题
                if len(set(question.topics).intersection(self.topics)) > 1:
                    continue
                asker = '' if question.author is ANONYMOUS else question.author.id
                QuestionManager.save_question(tid, question._url, question.id,
                                              question.creation_time, asker,
                                              question.title)
                task_queue.append(FetchQuestionInfo(tid, question))
            except (TypeError, IndexError):
                logger.exception(question.url)
            finally:
                question = next(it)
