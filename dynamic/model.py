# coding: utf-8

"""
ORM-like class
"""

import logging

import ezcf
import zhihu

from config.dynamic_config import topics
from db import DB

logger = logging.getLogger(__name__)


class QuestionModel:

    latest_question = {
        tid: None for tid in topics  # for cache
    }

    def __init__(self, tid, url=None, qid=None, asker=None, time=None, title=None,
                 question=None):
        """
        :param tid: fetched from which topic
        :param url: answer url
        :param qid: question id
        :param asker: question author id
        :param time: time question is raised
        :param title: question title
        :param question: zhihu.Question object
        """
        self.tid = tid
        if question:
            try:
                self.url = question.url
                self.qid = question.id
                if self.qid == '':
                    pass
                self.time = question.creation_time
                self.title = question.title
                if question.author:
                    self.asker = question.author.id
                else:
                    self.asker = ''  # 匿名用户, TODO: zhihu-py3增加ANONYMOUS常量
            except AttributeError:
                logging.exception("Error init QuestionModel\n")
        else:
            self.url = url
            self.qid = qid
            self.time = time
            self.asker = asker
            self.title = title
        self.answers = []

    @classmethod
    def is_latest(cls, tid, question):
        if cls.latest_question[tid]:
            print("latest: ", cls.latest_question[tid])
            return cls.latest_question[tid].qid == question.id
        else:
            doc = DB.find_latest_question(tid)
            if doc:
                cls.latest_question[tid] = cls.doc2question(doc)
                logger.debug("latest: " + str(cls.latest_question[tid]))
                return doc['qid'] == question.id
            else:
                # 第一次执行, 外部 set_latest 不会调用, 在这里初始化
                cls.set_latest(tid, question)
                logger.debug("latest: " + str(cls.latest_question[tid]))
                return True

    @classmethod
    def set_latest(cls, tid, question):
        """
        :param question: zhihu.Question object
        """
        logger.debug("Set latest question of %s to %s" % (topics[tid], question.id))
        cls.latest_question[tid] = cls(tid, question=question)

    def save(self):
        DB.save_question(self)

    @classmethod
    def get_all(cls, tid):
        questions = []
        for doc in DB.get_questions(tid):
            questions.append(cls.doc2question(doc))
        return questions

    @classmethod
    def doc2question(cls, doc):
        return cls(doc['topic'], doc['url'], doc['qid'], doc['asker'],
                   doc['time'], doc['title'])

    def __eq__(self, other):
        # title may change
        return self.url == other.url and self.qid == other.qid and \
               self.time == other.time and self.asker == other.asker

    def __str__(self):
        time_tuple = (self.time.hour, self.time.minute, self.time.second)
        return "{0}:{1}:{2} {3}".format(*time_tuple, self.title)


class AnswerModel:
    def __init__(self, tid, url=None, aid=None, qid=None, answerer=None, time=None,
                 upvoters=None, commenters=None, collectors=None, answer=None):
        """
        :param tid: fetched from which topic
        :param url: answer url
        :param aid: answer id
        :param qid: question id
        :param answerer: answer author's uid
        :param time: time when answer is posted
        :param upvoters: current upvoters
        :param commenters: current commenters
        :param collectors: current collectors
        :param answer: zhihu.Answer object
        """
        self.tid = tid
        if answer:
            try:
                self.url = answer.url
                self.aid = answer.id
                self.qid = answer.question.id
                self.answerer = answer.author.id
                self.time = answer.creation_time
                self.upvoters = [author.id for author in answer.upvoters]
                self.commenters = [comment.author.id for comment in answer.comments]
                self.collectors = [coll.owner.id for coll in answer.collections]
            except AttributeError:
                logging.exception("Error init AnswerModel\n")
        else:
            self.url = url
            self.aid = aid
            self.qid = qid
            self.answerer = answerer
            self.time = time
            self.upvoters = upvoters
            self.commenters = commenters
            self.collectors = collectors

    @classmethod
    def doc2answer(cls, doc):
        return cls(doc['topic'], doc['url'], doc['aid'], doc['qid'],
                   doc['answerer'], doc['time'], doc['upvoters'],
                   doc['commenters'], doc['collectors'])

    def __eq__(self, other):
        return self.url == other.url and self.aid == other.aid and \
               self.qid == other.qid and self.time == other.time and \
               self.answerer == other.answerer

    def __str__(self):
        time_tuple = (self.time.hour, self.time.minute, self.time.second)
        question_title = db.get_question(self.tid, self.qid)
        return "{0}:{1}:{2} {3} {4}".format(*time_tuple, self.answerer, question_title)

    def save(self):
        # save to db
        DB.save_answer(self)


class User:
    def __init__(self):
        pass

    def save(self):
        pass
