import requests
import time
import json
from main import get_header

def test_real_browser():
    """测试使用真实浏览器中的API端点"""
    # 用户提供的opus链接
    dynamic_id = "1167989808986849345"
    
    # 获取请求头
    header = get_header()
    print(f"获取到请求头: {header}")
    
    # 复制浏览器中的请求头
    browser_header = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'Referer': f'https://t.bilibili.com/{dynamic_id}',
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    # 合并请求头
    combined_header = {**header, **browser_header}
    print(f"\n合并后的请求头: {combined_header}")
    
    # 尝试获取动态评论
    print("\n=== 测试获取动态评论 ===")
    
    # 1. 尝试使用动态评论API
    print("\n1. 测试动态评论API")
    url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_reply"
    params = {
        'dynamic_id': dynamic_id,
        'offset': 0,
        'size': 20,
        'type': 0
    }
    
    try:
        resp = requests.get(url, headers=combined_header, params=params, timeout=10)
        print(f"响应状态码: {resp.status_code}")
        print(f"响应头: {resp.headers}")
        
        try:
            data = resp.json()
            print(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
        except json.JSONDecodeError:
            print(f"响应内容（非JSON）: {resp.text}")
            
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 2. 尝试使用评论API
    print("\n2. 测试评论API")
    url = "https://api.bilibili.com/x/v2/reply/main"
    params = {
        'oid': dynamic_id,
        'type': 17,
        'mode': 2,
        'pn': 1,
        'ps': 20,
        'sort': 2
    }
    
    try:
        resp = requests.get(url, headers=combined_header, params=params, timeout=10)
        print(f"响应状态码: {resp.status_code}")
        print(f"响应头: {resp.headers}")
        
        try:
            data = resp.json()
            print(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
        except json.JSONDecodeError:
            print(f"响应内容（非JSON）: {resp.text}")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    test_real_browser()
