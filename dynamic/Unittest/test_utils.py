"""
utils.py 中函数的测试
"""
import json
from datetime import datetime

import pytest
import freezegun

from utils import *
from common import *


def test_config_validator():
    config = json.load(open(dynamic_config_file, encoding='utf-8'))

    assert validate_config(config)

    config['topics']['11111'] = 'non-existent'
    with pytest.raises(InvalidTopicId):
        validate_config(config)
    del config['topics']['11111']

    config['restart'] = 10
    with pytest.raises(AssertionError):
        validate_config(config)
        config['restart'] = True

    del config['topics']
    with pytest.raises(LackConfig):
        validate_config(config)


def test_get_datetime_hour_min_sec():
    freezer = freezegun.freeze_time("2012-01-14 05:00:01")
    freezer.start()
    time_string = '04:35:45'
    year = datetime.now().year
    month = datetime.now().month
    day = datetime.now().day
    assert get_datetime_hour_min_sec(time_string) == \
           datetime(year, month, day, 4, 35, 45)

    time_string = '04:35'
    assert get_datetime_hour_min_sec(time_string + ':00') == \
           datetime(year, month, day, 4, 35, 0)
    freezer.stop()

    # 测试跨天
    freezer = freezegun.freeze_time("2012-01-14 00:00:01")
    freezer.start()
    time_string = '23:59'
    assert get_datetime_hour_min_sec(time_string + ':00') == \
           datetime(2012, 1, 13, 23, 59, 0)
    freezer.stop()


def test_get_datetime_day_month_year():
    time_string = '2016-01-01'
    assert get_datetime_day_month_year(time_string) == \
           datetime(2016, 1, 1, 0, 0, 0)
