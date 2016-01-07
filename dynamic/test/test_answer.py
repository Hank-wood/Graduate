import os
import time
import json
from datetime import datetime
from unittest.mock import patch, PropertyMock, Mock

from pymongo import MongoClient
import pytest

from model import AnswerModel
from db import DB
from utils import *
from common import *


@patch('task.FetchAnswerInfo.get_upvote_time', new=lambda x,y: datetime.now())
def test_fetch_answers_without_previous_data():
    # TODO: mock get_upvote/comment/collect_time
    obj = AnswerModel(tid='11')
    m = Mock(spec=obj)
    # print(m.u)
    print(m.url)
    # answer.aid, refresh(), upvoters, comments, collections
    # upvoter.id, comment.cid, comment.author.id, collection.id,
    # collection.onwer.id
    from task import FetchAnswerInfo
    print(FetchAnswerInfo.get_upvote_time(1, 1))


def test_fetch_answers_with_previous_data():
    pass
