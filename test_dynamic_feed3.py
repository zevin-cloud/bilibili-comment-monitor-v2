from main import get_header
import requests
import time

header = get_header()
mid = '349490448'

# 添加更多请求头
header['Origin'] = 'https://space.bilibili.com'
header['Referer'] = f'https://space.bilibili.com/{mid}/dynamic'

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

if resp.status_code == 200:
    data = resp.json()
    print(f'返回code: {data.get("code")}')
    print(f'返回message: {data.get("message")}')
    
    if data.get('code') == 0:
        items = data.get('data', {}).get('items', [])
        print(f'\n获取到 {len(items)} 条动态:')
        
        for item in items:
            dynamic_id = item.get('id_str')
            type_name = item.get('type')
            
            # 获取动态内容
            modules = item.get('modules', {})
            module_dynamic = modules.get('module_dynamic', {})
            desc = module_dynamic.get('desc', {})
            text = desc.get('text', '')[:50] if desc else ''
            
            # 获取视频信息
            major = module_dynamic.get('major', {})
            archive = major.get('archive', {})
            video_title = archive.get('title', '') if archive else ''
            video_bvid = archive.get('bvid', '') if archive else ''
            
            print(f'\n  动态ID: {dynamic_id}')
            print(f'  类型: {type_name}')
            print(f'  内容: {text}...')
            if video_bvid:
                print(f'  视频: {video_bvid} - {video_title}')
else:
    print(f'请求失败: {resp.status_code}')
