# coding: utf-8

import os
import sys
import time
import threading
import atexit
import json
import _thread
import logging
import logging.config
import concurrent.futures as cf
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import zhihu

from monitor import TopicMonitor
from utils import *
from common import *
from db import DB


def install_threadExcepthook():
    init_old = threading.Thread.__init__

    def init(self, *args, **kwargs):
        init_old(self, *args, **kwargs)
        run_old = self.run

        def run_with_except_hook(*args, **kw):
            try:
                run_old(*args, **kw)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                sys.excepthook(*sys.exc_info())
                _thread.interrupt_main()  # 保证主线程退出
        self.run = run_with_except_hook
    threading.Thread.__init__ = init


class AnswerTaskLoop(threading.Thread):

    def __init__(self, event, routine=None, *args, **kwargs):
        self.routine = routine
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.event = event
        self.multiple = 0   # ANSWER_TASKLOOP_INTERVAL 翻倍次数
        super().__init__(*args, **kwargs)

    def run(self):
        global cancelled_questions
        while True:
            start = time.time()

            if self.routine and callable(self.routine):
                self.routine()

            futures = []
            count = len(answer_task_queue)
            lst = set()
            for _ in range(count):
                task = answer_task_queue.popleft()
                if task.qid in cancelled_questions:
                    logger.info(task.answer.url + " cancelled with inactive q")
                    lst.add(task.qid)
                else:
                    futures.append(self.executor.submit(task.execute))

            cancelled_questions -= lst
            # wait for all tasks to complet
            # 即使用时超过也尽可能让它执行完
            cf.wait(futures, timeout=ANSWER_TASKLOOP_INTERVAL,
                    return_when=cf.ALL_COMPLETED)
            task_execution_time = time.time() - start
            logger.info("Answer tasks execution time is %d" % task_execution_time)

            if task_execution_time > MAX_ANSWER_TASK_EXECUTION_TIME:
                self.increase_interval()
                if not self.event.is_set():
                    self.event.set()  # set stop_fetch_questions_event
                    logger.warning("Stop fetching new questions")
            else:
                if self.multiple > 0:
                    self.decrease_interval()
                time.sleep(ANSWER_TASKLOOP_INTERVAL - task_execution_time)
                if fetch_new and self.event.is_set():
                    self.event.clear()  # unset stop_fetch_questions_event
                    logger.info("Start fetching new questions")

    @staticmethod
    def increase_interval():
        global ANSWER_TASKLOOP_INTERVAL
        ANSWER_TASKLOOP_INTERVAL *= 2
        self.multiple += 1

    @staticmethod
    def decrease_interval():
        global ANSWER_TASKLOOP_INTERVAL
        ANSWER_TASKLOOP_INTERVAL /= 2
        self.multiple -= 1


class QuestionTaskLoop(threading.Thread):

    def __init__(self, routine=None, *args, **kwargs):
        self.routine = routine
        self.executor = ThreadPoolExecutor(max_workers=20)
        super().__init__(*args, **kwargs)

    def run(self):
        while True:
            start = time.time()
            if self.routine and callable(self.routine):
                self.routine()

            futures = []
            count = len(question_task_queue)
            for _ in range(count):
                task = question_task_queue.popleft()
                futures.append(self.executor.submit(task.execute))

            cf.wait(futures, timeout=QUESTION_TASKLOOP_INTERVAL,
                    return_when=cf.ALL_COMPLETED)
            task_execution_time = time.time() - start
            logger.info("Question tasks execution time is %d" % task_execution_time)
            if task_execution_time < QUESTION_TASKLOOP_INTERVAL:
                time.sleep(QUESTION_TASKLOOP_INTERVAL - task_execution_time)


def configure():
    if os.path.isfile(logging_config_file):
        with open(logging_config_file, 'rt') as f:
            config = json.load(f)
            logging.config.dictConfig(config)

    logger = logging.getLogger(__name__)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    sys.modules[__name__].__dict__['logger'] = logger

    smtp_handler = logging.getLogger().handlers[2]
    assert isinstance(smtp_handler, logging.handlers.SMTPHandler)
    config_smtp_handler(smtp_handler)

    if restart:
        DB.drop_qa_collections()

    validate_config()

    if not validate_cookie(test_cookie):
        logger.error("invalid cookie")

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical("Uncaught exception",
                        exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception


def main(preroutine=None, postroutine=None):
    configure()
    logger.info("\n\n\nPROGRAM START\n")
    stop_fetch_questions_event = threading.Event()
    if not fetch_new:
        stop_fetch_questions_event.set()
    AnswerTaskLoop(stop_fetch_questions_event, daemon=True).start()
    QuestionTaskLoop(daemon=True).start()
    m = TopicMonitor()

    while True:
        start = time.time()
        if preroutine and callable(preroutine):
            preroutine()

        if not stop_fetch_questions_event.is_set():
            m.detect_new_question()

        try:
            if postroutine and callable(postroutine):
                postroutine()
        except EndProgramException:
            break

        task_execution_time = time.time() - start
        if FETCH_QUESTION_INTERVAL > task_execution_time:
            time.sleep(FETCH_QUESTION_INTERVAL - task_execution_time)


def cleaning():
    DB.db.client.close()
    logger.info("PROGRAM EXIT\n\n\n")


if __name__ == '__main__':
    install_threadExcepthook()
    atexit.register(cleaning)
    main()
