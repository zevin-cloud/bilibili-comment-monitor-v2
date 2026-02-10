from main import get_header
import requests
import time
import hashlib
import urllib.parse

header = get_header()
mid = '349490448'

# 添加更多请求头
header['Origin'] = 'https://space.bilibili.com'
header['Referer'] = f'https://space.bilibili.com/{mid}/dynamic'

# 尝试使用旧的动态API
print('尝试使用旧版动态API...')
url = f"https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history"
params = {
    'host_uid': mid,
    'offset_dynamic_id': 0,
    'need_top': 1
}

resp = requests.get(url, headers=header, params=params, timeout=10)
print(f'状态码: {resp.status_code}')

if resp.status_code == 200:
    data = resp.json()
    print(f'返回code: {data.get("code")}')
    print(f'返回message: {data.get("message")}')
    
    if data.get('code') == 0:
        cards = data.get('data', {}).get('cards', [])
        print(f'\n获取到 {len(cards)} 条动态:')
        
        for card in cards[:5]:
            desc = card.get('desc', {})
            dynamic_id = desc.get('dynamic_id')
            dynamic_type = desc.get('type')
            
            # 解析card内容
            import json
            try:
                card_content = json.loads(card.get('card', '{}'))
                item = card_content.get('item', {})
                content = item.get('content', '')[:50] if isinstance(item, dict) else ''
            except:
                content = '[无法解析]'
            
            print(f'\n  动态ID: {dynamic_id}')
            print(f'  类型: {dynamic_type}')
            print(f'  内容: {content}...')
else:
    print(f'请求失败: {resp.status_code}')
    print(f'响应: {resp.text[:200]}')
