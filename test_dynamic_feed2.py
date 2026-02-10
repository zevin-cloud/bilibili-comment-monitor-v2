from main import get_header
import requests
import time

header = get_header()
mid = '349490448'

# 获取用户动态
print('获取用户动态...')
url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
params = {
    'host_mid': mid,
    'offset': '',
    'page': 1,
    'timezone_offset': -480
}

resp = requests.get(url, headers=header, params=params, timeout=10)
print(f'状态码: {resp.status_code}')
print(f'Content-Type: {resp.headers.get("Content-Type")}')
print(f'响应长度: {len(resp.text)}')
print(f'响应前500字符:')
print(resp.text[:500])
