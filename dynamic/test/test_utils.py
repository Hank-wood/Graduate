"""
utils.py 中函数的测试
"""
import utils
from datetime import datetime


def test_get_datetime_hour_min_sec():
    time_string = '04:35:45'
    year = datetime.now().year
    month = datetime.now().month
    day = datetime.now().day
    assert utils.get_datetime_hour_min_sec(time_string) == \
           datetime(year, month, day, 4, 35, 45)

    time_string = '04:35'
    assert utils.get_datetime_hour_min_sec(time_string + ':00') == \
           datetime(year, month, day, 4, 35, 0)


def test_get_datetime_day_month_year():
    time_string = '2016-01-01'
    assert utils.get_datetime_day_month_year(time_string) == \
           datetime(2016, 1, 1, 0, 0, 0)