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


class TaskLoop(threading.Thread):

    def __init__(self, event, routine=None, *args, **kwargs):
        self.routine = routine
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.event = event
        super().__init__(*args, **kwargs)

    def run(self):
        logger = logging.getLogger(__name__)
        while True:
            start = time.time()

            if self.routine and callable(self.routine):
                self.routine()

            futures = []
            count = len(task_queue)
            for _ in range(count):
                task = task_queue.popleft()
                futures.append(self.executor.submit(task.execute))

            # wait for all tasks to complete
            cf.wait(futures, return_when=cf.ALL_COMPLETED)
            task_execution_time = time.time() - start

            if not self.event.is_set() and task_execution_time > MAX_TASK_EXECUTION_TIME:
                self.event.set()  # set stop_fetch_questions_event
                logger.warning("Task execution time is %d"% task_execution_time)
                logger.info("Stop fetching new questions")
            else:
                logger.info("Task execution time is %d" % task_execution_time)
                if TASKLOOP_INTERVAL > task_execution_time:
                    time.sleep(TASKLOOP_INTERVAL - task_execution_time)


def configure():
    if os.path.isfile(logging_config_file):
        with open(logging_config_file, 'rt') as f:
            config = json.load(f)
            logging.config.dictConfig(config)

    logger = logging.getLogger(__name__)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    smtp_handler = logging.getLogger().handlers[2]
    assert isinstance(smtp_handler, logging.handlers.SMTPHandler)

    with open(smtp_config_file, 'rt') as f:
        smtp_config = json.load(f)
        smtp_handler.username, smtp_handler.password = \
            smtp_config['username'], smtp_config['password']

    if restart:
        DB.drop_all_collections()

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
    stop_fetch_questions_event = threading.Event()
    if fetch_new == False:
        stop_fetch_questions_event.set()
    TaskLoop(stop_fetch_questions_event, daemon=True).start()
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


if __name__ == '__main__':
    install_threadExcepthook()
    atexit.register(cleaning)
    main()
