import os
import json
import logging
import logging.config
import threading
from datetime import datetime

from flask import Flask
from concurrent.futures import ThreadPoolExecutor

import follower
from common import *

executor = ThreadPoolExecutor(max_workers=10)
app = Flask(__name__)


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


@app.route("/follower/<uid>")
def hello(uid):
    executor.submit(follower.fetch_followers, uid, datetime.now())
    return "Hello World!"


def main():
    if os.path.isfile(logging_config_file):
        with open(logging_config_file, 'rt') as f:
            config = json.load(f)
            logging.config.dictConfig(config)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    install_threadExcepthook()
    app.run()


if __name__ == "__main__":
    main()
