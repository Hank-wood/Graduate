# coding: utf-8

"""
定义任务类
"""

from concurrent.futures import ThreadPoolExecutor


class Task:

    executor = ThreadPoolExecutor(max_workers=4)


class FetchNewAnswer(Task):
    def __init__(self):
        pass

    def execute(self):
        print("execute task: fetch new answer")


class FetchAnswerInfo(Task):
    pass


__all__ = [
    'FetchNewAnswer',
    'FetchAnswerInfo'
]