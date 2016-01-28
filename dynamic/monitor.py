# coding: utf-8

"""
定期爬话题页面
"""

import logging

import ezcf
import requests

from config.dynamic_config import topics
from task import *
from manager import QuestionManager
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

    @staticmethod
    def _load_old_question():
        # 数据库中已有的 question 加入 task queue, answer 不用管
        session = requests.Session()
        logger.info('Loading old questions from database............')

        for question in QuestionManager.get_all_questions():
            url = question['url'] if question['url'].endswith('?sort=created') \
                  else question['url'][:-1] + '?sort=created'
            task_queue.append(FetchQuestionInfo(tid=question['topic'],
                                                question=Question(url,
                                                               session=session),
                                                from_db=True))

        logger.info('Loading old questions from database succeed :)')

    def detect_new_question(self):
        """
        爬取话题页面，寻找新问题
        """
        for topic in self.topics:
            tid = str(topic.id)
            it = iter(topic.questions)
            question = latest_question = next(it)

            # new logic
            if QuestionManager.latest_question[tid] is None:
                QuestionManager.set_latest(tid, latest_question)
            else:
                new_questions = []
                while QuestionManager.latest_question[tid] != question.id:
                    question._url = question.url[:-1] + '?sort=created'
                    new_questions.append(question)
                    if question.author:
                        asker = question.author.id
                    else:
                        asker = ''  # 匿名用户, TODO: zhihu-py3增加ANONYMOUS常量
                    QuestionManager.save(tid, question._url, question.qid,
                                         question.creation_time, asker,
                                         question.title)
                    task_queue.append(FetchQuestionInfo(tid, question))
                    question = next(it)

                if new_questions:
                    QuestionManager.set_latest(tid, latest_question)

