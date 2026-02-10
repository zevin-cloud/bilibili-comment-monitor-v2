import requests
import json
import time
import urllib.parse

# 从文件读取cookie
with open('bili_cookie.txt', 'r', encoding='utf-8') as f:
    cookie = f.read().strip()

header = {
    "Cookie": cookie,
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    "Referer": "https://www.bilibili.com"
}

oid = '113622675998173'
mixin_key_salt = "ea1db124af3c7062474693fa704f4ff8"

params = {'oid': oid, 'type': 1, 'mode': 2, 'plat': 1, 'web_location': 1315875, 'wts': int(time.time())}
query_for_w_rid = urllib.parse.urlencode(sorted(params.items()))

import hashlib
MD5 = hashlib.md5()
MD5.update((query_for_w_rid + mixin_key_salt).encode('utf-8'))
w_rid = MD5.hexdigest()

params['w_rid'] = w_rid
url = f"https://api.bilibili.com/x/v2/reply/wbi/main?{urllib.parse.urlencode(params)}"

print(f'请求URL: {url[:120]}...')
response = requests.get(url, headers=header, timeout=5)
print(f'状态码: {response.status_code}')

data = response.json()
print(f'响应code: {data.get("code")}')
print(f'响应message: {data.get("message")}')
print(f'是否有data: {"data" in data}')
if data.get('data'):
    replies = data['data'].get('replies', [])
    print(f'评论数量: {len(replies) if replies else 0}')
