from main import get_header
import user_monitor
import requests
import time
import hashlib
import urllib.parse

header = get_header()
mid = '349490448'

# 直接使用API获取原始数据
url = f"https://api.bilibili.com/x/space/wbi/arc/search"

mixin_key_salt = "ea1db124af3c7062474693fa704f4ff8"
params = {
    'mid': mid,
    'ps': 20,
    'tid': 0,
    'pn': 1,
    'keyword': '',
    'order': 'pubdate',
    'platform': 'web',
    'web_location': '1550101',
    'order_avoided': 'true',
    'wts': int(time.time())
}

query_for_w_rid = urllib.parse.urlencode(sorted(params.items()))
w_rid = hashlib.md5((query_for_w_rid + mixin_key_salt).encode('utf-8')).hexdigest()
params['w_rid'] = w_rid

print(f'请求URL: {url}')
print(f'参数: {params}')
print()

resp = requests.get(url, headers=header, params=params, timeout=10)
data = resp.json()

print(f'返回code: {data.get("code")}')
print(f'返回message: {data.get("message")}')

if data.get('code') == 0:
    list_data = data.get('data', {}).get('list', {})
    vlist = list_data.get('vlist', [])
    page = data.get('data', {}).get('page', {})
    
    print(f'总视频数: {page.get("count", 0)}')
    print(f'当前页视频数: {len(vlist)}')
    print()
    print('视频列表:')
    for item in vlist:
        print(f'  - {item.get("bvid")}: {item.get("title")} (发布时间: {item.get("created")})')
