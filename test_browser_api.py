import requests
import time
import json
from main import get_header

def test_browser_api():
    """测试使用浏览器开发者工具中常见的API端点"""
    # 用户提供的opus链接
    opus_url = "https://www.bilibili.com/opus/1167989808986849345"
    dynamic_id = "1167989808986849345"
    
    # 获取请求头
    header = get_header()
    print(f"获取到请求头: {header}")
    
    # 尝试使用浏览器中常见的API端点
    print("\n=== 测试浏览器常见API端点 ===")
    
    # 1. 尝试获取动态详情（浏览器中常见）
    print("\n1. 测试获取动态详情")
    url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail"
    params = {'dynamic_id': dynamic_id}
    
    try:
        resp = requests.get(url, headers=header, params=params, timeout=10)
        print(f"响应状态码: {resp.status_code}")
        data = resp.json()
        print(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 2. 尝试获取评论（使用不同的API端点）
    print("\n2. 测试获取评论")
    urls_to_try = [
        # 动态评论API
        ("https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_reply", {
            'dynamic_id': dynamic_id,
            'offset': 0,
            'size': 20
        }),
        # 评论主API
        ("https://api.bilibili.com/x/v2/reply/main", {
            'oid': dynamic_id,
            'type': 17,
            'mode': 2,
            'pn': 1,
            'ps': 20
        }),
        # 评论API（不使用wbi）
        ("https://api.bilibili.com/x/v2/reply", {
            'oid': dynamic_id,
            'type': 17,
            'pn': 1,
            'ps': 20,
            'sort': 2
        })
    ]
    
    for url, params in urls_to_try:
        print(f"\n尝试API: {url}")
        print(f"参数: {params}")
        
        try:
            # 复制请求头
            header_copy = header.copy()
            header_copy['Referer'] = f'https://t.bilibili.com/{dynamic_id}'
            
            # 发送请求
            resp = requests.get(url, headers=header_copy, params=params, timeout=10)
            print(f"响应状态码: {resp.status_code}")
            
            # 尝试解析响应
            try:
                data = resp.json()
                print(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except json.JSONDecodeError:
                print(f"响应内容（非JSON）: {resp.text[:200]}...")
                
        except Exception as e:
            print(f"请求失败: {e}")

if __name__ == "__main__":
    test_browser_api()
