# coding: utf-8

import os
import sys
import time
import threading
import atexit
import json
import logging
import logging.config
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import zhihu

from monitor import TopicMonitor
from utils import *
from utils import task_queue
from common import *
from config.dynamic_config import restart
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
        self.run = run_with_except_hook
    threading.Thread.__init__ = init


class TaskLoop(threading.Thread):

    def __init__(self, routine=None, *args, **kwargs):
        self.routine = routine
        self.executor = ThreadPoolExecutor(max_workers=10)
        super().__init__(*args, **kwargs)

    def run(self):
        while True:
            if self.routine and callable(self.routine):
                self.routine()
            time.sleep(10)  # TODO: set to 60s
            count = len(task_queue)
            for _ in range(count):
                task = task_queue.popleft()
                self.executor.submit(task.execute)


def configure():
    if os.path.isfile(logging_config_file):
        with open(logging_config_file, 'rt') as f:
            config = json.load(f)
            logging.config.dictConfig(config)
            log_dir = os.path.dirname(config['handlers']['file_handler']['filename'])
            os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(__name__)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    if restart:
        DB.drop_all_collections()
    else:
        pass
        # get all questions from db, make zhihu.question
        # task_queue.append(FetchNewAnswer(question))

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
    client = zhihu.ZhihuClient(test_cookie)
    TaskLoop(daemon=True).start()
    m = TopicMonitor(client)

    while True:
        # TODO: 考虑新问题页面采集消耗的时间，不能 sleep 60s
        if preroutine and callable(preroutine):
            preroutine()

        time.sleep(10)
        m.detect_new_question()

        try:
            if postroutine and callable(postroutine):
                postroutine()
        except EndProgramException:
            break


def cleaning():
    """
    Only for testing
    """
    from db import DB
    for collection in DB.db.collection_names():
        db[collection].drop()


if __name__ == '__main__':
    install_threadExcepthook()
    main()
    # atexit.register(cleaning)