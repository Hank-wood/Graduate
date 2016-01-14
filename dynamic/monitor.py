# coding: utf-8

"""
定期爬话题页面
"""

import logging

import ezcf

from config.dynamic_config import topics
from task import *
from model import QuestionManager
from utils import task_queue
from common import *
from zhihu.question import Question

logger = logging.getLogger(__name__)


class TopicMonitor:

    def __init__(self, client):
        self.client = client
        self.topics = [
            client.topic(TOPIC_PREFIX + tid) for tid in topics
        ]
        self._load_old_question()

    def _load_old_question(self):
        # 数据库中已有的 question 加入 task queue, answer 不用管
        # TODO: reuse session?
        logger.info('Loading old questions from database............')
        for question in QuestionManager.get_all_questions():
            url = question['url'] if question['url'].endswith('?sort=created') \
                  else question['url'][:-1] + '?sort=created'
            task_queue.append(FetchNewAnswer(tid=question['topic'],
                                             question=Question(url),
                                             from_db=True))

        logger.info('Loading old questions from database succeed :)')

    def detect_new_question(self):
        """
        爬取话题页面，寻找新问题
        :return:
        """
        for topic in self.topics:
            tid = str(topic.id)
            it = iter(topic.questions)
            question = latest_question = next(it)
            new_questions = []

            while not QuestionManager.is_latest(tid, question):
                question._url = question.url[:-1] + '?sort=created'
                new_questions.append(question)
                task_queue.append(FetchNewAnswer(tid, question))
                QuestionManager(tid, question=question).save()
                question = next(it)

            if new_questions:
                QuestionManager.set_latest(tid, latest_question)

