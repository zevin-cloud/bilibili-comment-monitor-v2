import requests
import time
import hashlib
import urllib.parse
import json
from main import get_header

def md5(code):
    """对输入字符串执行 MD5 哈希。"""
    MD5 = hashlib.md5()
    MD5.update(code.encode('utf-8'))
    return MD5.hexdigest()

def get_wbi_keys(header):
    """动态获取 WBI 签名所需的 img_key 和 sub_key"""
    try:
        resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=header, timeout=5)
        resp.raise_for_status()
        json_content = resp.json()
        img_url = json_content['data']['wbi_img']['img_url']
        sub_url = json_content['data']['wbi_img']['sub_url']
        img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
        return img_key, sub_key
    except Exception as e:
        print(f"动态获取 WBI keys 失败: {e}，将使用备用盐值")
        return None, None

def enc_wbi(params, img_key, sub_key):
    """为请求参数添加 WBI 签名"""
    mixin_key_enc_tab = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]
    raw_key = img_key + sub_key
    mixin_key = "".join([raw_key[i] for i in mixin_key_enc_tab])[:32]
    curr_time = int(time.time())
    params['wts'] = curr_time
    params = dict(sorted(params.items()))
    # 过滤特殊字符
    params = {
        k: "".join([char for char in str(v) if char not in "!'()*"]) 
        for k, v in params.items()
    }
    query = urllib.parse.urlencode(params)
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = w_rid
    return params

def test_opus_comments():
    """测试获取专栏动态评论"""
    # 用户提供的opus链接
    opus_url = "https://www.bilibili.com/opus/1167989808986849345"
    opus_id = "1167989808986849345"
    column_id = None  # 专栏实际ID
    
    # 获取请求头
    header = get_header()
    print(f"获取到请求头: {header}")
    
    # 获取 WBI 签名所需的 keys
    img_key, sub_key = get_wbi_keys(header)
    print(f"WBI keys: img_key={img_key}, sub_key={sub_key}")
    
    # 首先获取动态的详细信息
    print("\n=== 测试获取动态详细信息 ===")
    url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail"
    params = {
        'dynamic_id': opus_id
    }
    
    try:
        resp = requests.get(url, headers=header, params=params, timeout=10)
        print(f"响应状态码: {resp.status_code}")
        data = resp.json()
        print(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        if data.get('code') == 0:
            dynamic_data = data.get('data', {})
            desc = dynamic_data.get('desc', {})
            print(f"动态类型: {desc.get('type', '未知')}")
            print(f"动态作者: {desc.get('user_profile', {}).get('info', {}).get('uname', '未知')}")
            print(f"评论数: {desc.get('comment', '未知')}")
            
            # 获取专栏实际ID
            column_id = desc.get('rid', None)
            print(f"专栏实际ID (rid): {column_id}")
            
            # 尝试从card字段解析专栏ID
            card_str = dynamic_data.get('card', {}).get('card', '')
            if card_str:
                try:
                    card_json = json.loads(card_str)
                    if 'id' in card_json:
                        column_id = card_json['id']
                        print(f"从card字段解析到专栏ID: {column_id}")
                except json.JSONDecodeError as e:
                    print(f"解析card字段失败: {e}")
        else:
            print(f"获取动态详细信息失败: {data.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"请求动态详细信息时出错: {e}")
    
    # 测试专栏评论专用API
    if column_id:
        print(f"\n=== 测试专栏评论专用API - 使用专栏ID {column_id} ===")
        url = "https://api.bilibili.com/x/article/reply/list"
        params = {
            'id': column_id,
            'pn': 1,
            'ps': 20,
            'sort': 2
        }
        
        # 添加 WBI 签名
        if img_key and sub_key:
            params = enc_wbi(params, img_key, sub_key)
        else:
            # 退回到旧的硬编码方式（备用）
            mixin_key_salt = "ea1db124af3c7062474693fa704f4ff8"
            params['wts'] = int(time.time())
            params = dict(sorted(params.items()))
            query_for_w_rid = urllib.parse.urlencode(params)
            params['w_rid'] = md5(query_for_w_rid + mixin_key_salt)
        
        # 构建完整的URL
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        print(f"请求URL: {full_url}")
        
        # 只保留必要的请求头
        header_copy = header.copy()
        header_copy['Referer'] = f'https://www.bilibili.com/opus/{opus_id}'
        # 移除可能导致问题的请求头
        headers_to_remove = ['Origin', 'Sec-Fetch-Dest', 'Sec-Fetch-Mode', 'Sec-Fetch-Site', 'Sec-Ch-Ua', 'Sec-Ch-Ua-Mobile', 'Sec-Ch-Ua-Platform']
        for key in headers_to_remove:
            if key in header_copy:
                del header_copy[key]
        
        try:
            resp = requests.get(url, headers=header_copy, params=params, timeout=10)
            print(f"响应状态码: {resp.status_code}")
            data = resp.json()
            print(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get('code') == 0:
                reply_data = data.get('data', {})
                # 检查不同的数据结构
                if 'replies' in reply_data:
                    replies = reply_data['replies']
                    print(f"获取到 {len(replies)} 条评论")
                    for i, reply in enumerate(replies[:3]):  # 只显示前3条
                        if 'member' in reply and 'content' in reply:
                            member = reply['member']
                            content = reply['content']
                            print(f"评论 {i+1}: {member.get('uname')}: {content.get('message')[:50]}...")
                        elif 'user' in reply and 'comment' in reply:
                            user = reply['user']
                            comment = reply['comment']
                            print(f"评论 {i+1}: {user.get('uname')}: {comment.get('message')[:50]}...")
                elif 'list' in reply_data and 'replies' in reply_data['list']:
                    replies = reply_data['list']['replies']
                    print(f"获取到 {len(replies)} 条评论")
                    for i, reply in enumerate(replies[:3]):  # 只显示前3条
                        if 'member' in reply and 'content' in reply:
                            member = reply['member']
                            content = reply['content']
                            print(f"评论 {i+1}: {member.get('uname')}: {content.get('message')[:50]}...")
            else:
                print(f"API 获取评论失败: {data.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"请求评论时出错: {e}")
    else:
        print("\n未获取到专栏ID，跳过专栏评论测试")
    
    # 测试动态评论API（类型17）
    print("\n=== 测试动态评论API（类型17）===")
    url = "https://api.bilibili.com/x/v2/reply/wbi/main"
    params = {
        'oid': opus_id,
        'type': 17,  # 动态评论类型
        'mode': 2,
        'plat': 1,
        'web_location': 1315875
    }
    
    # 添加 WBI 签名
    if img_key and sub_key:
        params = enc_wbi(params, img_key, sub_key)
    else:
        # 退回到旧的硬编码方式（备用）
        mixin_key_salt = "ea1db124af3c7062474693fa704f4ff8"
        params['wts'] = int(time.time())
        params = dict(sorted(params.items()))
        query_for_w_rid = urllib.parse.urlencode(params)
        params['w_rid'] = md5(query_for_w_rid + mixin_key_salt)
    
    # 构建完整的URL
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    print(f"请求URL: {full_url}")
    
    # 只保留必要的请求头
    header_copy = header.copy()
    header_copy['Referer'] = f'https://t.bilibili.com/{opus_id}'
    # 移除可能导致问题的请求头
    headers_to_remove = ['Origin', 'Sec-Fetch-Dest', 'Sec-Fetch-Mode', 'Sec-Fetch-Site', 'Sec-Ch-Ua', 'Sec-Ch-Ua-Mobile', 'Sec-Ch-Ua-Platform']
    for key in headers_to_remove:
        if key in header_copy:
            del header_copy[key]
    
    try:
        resp = requests.get(url, headers=header_copy, params=params, timeout=10)
        print(f"响应状态码: {resp.status_code}")
        data = resp.json()
        print(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        if data.get('code') == 0:
            reply_data = data.get('data', {})
            # 检查不同的数据结构
            if 'replies' in reply_data:
                replies = reply_data['replies']
                print(f"获取到 {len(replies)} 条评论")
                for i, reply in enumerate(replies[:3]):  # 只显示前3条
                    if 'member' in reply and 'content' in reply:
                        member = reply['member']
                        content = reply['content']
                        print(f"评论 {i+1}: {member.get('uname')}: {content.get('message')[:50]}...")
                    elif 'user' in reply and 'comment' in reply:
                        user = reply['user']
                        comment = reply['comment']
                        print(f"评论 {i+1}: {user.get('uname')}: {comment.get('message')[:50]}...")
            elif 'list' in reply_data and 'replies' in reply_data['list']:
                replies = reply_data['list']['replies']
                print(f"获取到 {len(replies)} 条评论")
                for i, reply in enumerate(replies[:3]):  # 只显示前3条
                    if 'member' in reply and 'content' in reply:
                        member = reply['member']
                        content = reply['content']
                        print(f"评论 {i+1}: {member.get('uname')}: {content.get('message')[:50]}...")
        else:
            print(f"API 获取评论失败: {data.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"请求评论时出错: {e}")

if __name__ == "__main__":
    test_opus_comments()
