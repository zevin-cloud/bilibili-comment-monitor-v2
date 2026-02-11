import requests
import time
import json
from main import get_header

def test_browser_emulation():
    """测试模拟真实浏览器的请求方式"""
    # 用户提供的opus链接
    dynamic_id = "1167989808986849345"
    
    # 获取请求头
    header = get_header()
    print(f"获取到请求头: {header}")
    
    # 模拟真实浏览器的请求头
    browser_header = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Origin': 'https://t.bilibili.com',
        'Referer': f'https://t.bilibili.com/{dynamic_id}',
        'Sec-Ch-Ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
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
        # 添加随机延迟，模拟真实用户行为
        time.sleep(1)
        
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
    
    # 2. 尝试使用评论API（带WBI签名）
    print("\n2. 测试评论API（带WBI签名）")
    from user_monitor import get_wbi_keys, enc_wbi
    
    # 获取WBI keys
    img_key, sub_key = get_wbi_keys(combined_header)
    print(f"WBI keys: img_key={img_key}, sub_key={sub_key}")
    
    # 构建请求参数
    url = "https://api.bilibili.com/x/v2/reply/wbi/main"
    params = {
        'oid': dynamic_id,
        'type': 17,
        'mode': 2,
        'pn': 1,
        'ps': 20,
        'sort': 2
    }
    
    # 添加WBI签名
    if img_key and sub_key:
        params = enc_wbi(params, img_key, sub_key)
        print(f"添加WBI签名后的参数: {params}")
    
    try:
        # 添加随机延迟，模拟真实用户行为
        time.sleep(1)
        
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
    test_browser_emulation()
