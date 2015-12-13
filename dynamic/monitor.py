# coding: utf-8

"""
定期爬话题页面
"""

from task import *


class TopicMonitor:

    topic_links = [
        'https://www.zhihu.com/topic/19552330'  # 程序员
    ]
    # TODO: 应该初始化最新问题
    latest_questions = {link: None for link in topic_links}  # question id

    def __init__(self, client, queue):
        self.client = client
        self.task_queue = queue
        self.topics = [client.Topic(link) for link in self.topic_links]

    def detect_new_question(self):
        """
        爬取话题页面，寻找新问题
        :return:
        """
        for topic in self.topics:
            for question in topic.questions:
                if question.id == self.latest_questions[topic.url]:
                    break
                else:
                    self.task_queue.append(FetchNewAnswer(question))

