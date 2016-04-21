from zhihu import ZhihuClient

cookie = '../../cookies/zhuoyi.json'
client = ZhihuClient(cookie)
"""
import os
from zhihu_oauth import ZhihuClient


TOKEN_FILE = 'token.pkl'
client = ZhihuClient()
if os.path.isfile(TOKEN_FILE):
    client.load_token(TOKEN_FILE)
else:
    client.login_in_terminal()
    client.save_token(TOKEN_FILE)
"""
