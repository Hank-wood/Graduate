# coding: utf-8

"""
定期爬话题页面
"""

import ezcf

from config.dynamic_config import topics
from task import *
from model import QuestionModel


class TopicMonitor:

    PREFIX = "http://www.zhihu.com/topic/"

    def __init__(self, client, queue):
        self.client = client
        self.task_queue = queue
        self.topics = [
            client.topic(self.PREFIX+tid) for tid in topics
        ]

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

            while not QuestionModel.is_latest(tid, question):
                new_questions.append(question)
                self.task_queue.append(FetchNewAnswer(question))
                QuestionModel(question).save()
                question = next(it)

            if new_questions:  # TODO: 第一次有问题
                QuestionModel.set_latest(tid, latest_question)
