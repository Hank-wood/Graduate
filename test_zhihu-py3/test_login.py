# coding: utf-8

import os
import platform
from threading import Timer
from zhihu import ZhihuClient

cookie = '../cookies/zhuoyi.json'
client = ZhihuClient()


def check_and_open_captcha():
    if os.path.isfile('captcha.gif'):
        if platform.system() == 'Darwin':
            os.system('open captcha.gif')
        elif platform.system() == 'Windows':
            os.system('captcha.gif')
    else:
        Timer(5, check_and_open_captcha).start()


def login():
    if os.path.isfile(cookie):
        with open(cookie) as f:
            client.login_with_cookies(f.read())
    else:
        with open(cookie, 'w') as f:
            cookies = client.login_in_terminal()
            print(cookies)
            f.write(cookies)
        # code, msg, cookies = client.login(email, password, captcha)


def display_vzch():
    url = 'http://www.zhihu.com/people/excited-vczh'
    author = client.author(url)

    print('用户名 %s' % author.name)
    print('用户简介 %s' % author.motto)
    print('用户关注人数 %d' % author.followee_num)
    print('取用户粉丝数 %d' % author.follower_num)
    print('用户得到赞同数 %d' % author.upvote_num)
    print('用户得到感谢数 %d' % author.thank_num)
    print('用户提问数 %d' % author.question_num)
    print('用户答题数 %d' % author.answer_num)


if __name__ == '__main__':
    if os.path.isfile('captcha.gif'):
        os.remove('captcha.gif')
    # check_and_open_captcha()
    login()
    display_vzch()
