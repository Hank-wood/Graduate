# coding: utf-8

"""
定期爬话题页面
"""

import ezcf
from requests.adapters import HTTPAdapter

from config.dynamic_config import topics
from task import *
from model import QuestionManager
from utils import task_queue
from common import *


class TopicMonitor:

    def __init__(self, client):
        self.client = client
        self.topics = [
            client.topic(TOPIC_PREFIX + tid) for tid in topics
        ]
        # in case connection reset by server
        for t in self.topics:
            t._session.mount('https://', HTTPAdapter(max_retries=5))

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

