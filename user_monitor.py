# filename: user_monitor.py
import requests
import time
import hashlib
import urllib.parse
import json


def md5(code):
    """对输入字符串执行 MD5 哈希。"""
    MD5 = hashlib.md5()
    MD5.update(code.encode('utf-8'))
    return MD5.hexdigest()


def get_user_info(mid, header):
    """
    通過用戶ID獲取用戶信息。
    
    Args:
        mid: 用戶ID
        header: 請求頭
        
    Returns:
        (uname, face) 或 (None, None)
    """
    url = f"https://api.bilibili.com/x/web-interface/card?mid={mid}"
    try:
        resp = requests.get(url, headers=header, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') == 0:
            card = data.get('data', {}).get('card', {})
            uname = card.get('name')
            face = card.get('face')
            return uname, face
    except Exception as e:
        print(f"獲取用戶 {mid} 信息時出錯: {e}")
    return None, None
def get_user_dynamic_videos(mid, header, limit=10):
    """
    獲取用戶最新發布的視頻（從動態中獲取）。
    
    Args:
        mid: 用戶ID
        header: 請求頭
        limit: 最多獲取多少個視頻
        
    Returns:
        [(bvid, title), ...] 列表
    """
    videos = []
    # 使用 space 接口獲取用戶投稿視頻
    url = f"https://api.bilibili.com/x/space/wbi/arc/search"
    
    # 構建 wbi 簽名參數
    mixin_key_salt = "ea1db124af3c7062474693fa704f4ff8"
    params = {
        'mid': mid,
        'ps': limit,
        'tid': 0,
        'pn': 1,
        'keyword': '',
        'order': 'pubdate',  # 按發布時間排序
        'platform': 'web',
        'web_location': '1550101',
        'order_avoided': 'true',
        'wts': int(time.time())
    }
    
    # 計算 w_rid
    query_for_w_rid = urllib.parse.urlencode(sorted(params.items()))
    w_rid = md5(query_for_w_rid + mixin_key_salt)
    params['w_rid'] = w_rid
    
    try:
        resp = requests.get(url, headers=header, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('code') == 0:
            vlist = data.get('data', {}).get('list', {}).get('vlist', [])
            for item in vlist:
                bvid = item.get('bvid')
                title = item.get('title')
                if bvid and title:
                    videos.append((bvid, title))
        else:
            print(f"獲取用戶 {mid} 視頻列表失敗: {data.get('message', '未知錯誤')}")
            
    except Exception as e:
        print(f"請求用戶 {mid} 視頻列表時出錯: {e}")
    
    return videos


def get_user_dynamics(mid, header, limit=20):
    """
    获取用户的动态列表（包括文字、图片、视频等）。
    
    Args:
        mid: 用户ID
        header: 请求头
        limit: 最多获取多少条动态
        
    Returns:
        [{
            'dynamic_id': 动态ID,
            'type': 动态类型,
            'content': 动态内容,
            'timestamp': 发布时间戳,
            'bvid': 视频BV号（如果是视频动态）,
            'video_title': 视频标题（如果是视频动态）
        }, ...]
    """
    dynamics = []
    
    # 添加必要的请求头
    header_copy = header.copy()
    header_copy['Origin'] = 'https://space.bilibili.com'
    header_copy['Referer'] = f'https://space.bilibili.com/{mid}/dynamic'
    
    url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history"
    params = {
        'host_uid': mid,
        'offset_dynamic_id': 0,
        'need_top': 1
    }
    
    try:
        resp = requests.get(url, headers=header_copy, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('code') == 0:
            cards = data.get('data', {}).get('cards', [])
            
            for card in cards[:limit]:
                desc = card.get('desc', {})
                dynamic_id = str(desc.get('dynamic_id', ''))
                dynamic_type = desc.get('type', 0)
                timestamp = desc.get('timestamp', 0)
                
                # 解析card内容
                content = ''
                bvid = ''
                video_title = ''
                
                try:
                    card_content = json.loads(card.get('card', '{}'))
                    
                    # 根据动态类型解析内容
                    if dynamic_type == 8:  # 视频动态
                        bvid = card_content.get('bvid', '')
                        video_title = card_content.get('title', '')
                        content = card_content.get('dynamic', '')[:100]
                    elif dynamic_type == 64:  # 专栏动态
                        content = card_content.get('summary', '')[:100]
                    elif dynamic_type == 2:  # 图片动态
                        item = card_content.get('item', {})
                        content = item.get('description', '')[:100]
                    elif dynamic_type == 4:  # 文字动态
                        item = card_content.get('item', {})
                        content = item.get('content', '')[:100]
                    elif dynamic_type == 1:  # 转发动态
                        item = card_content.get('item', {})
                        content = item.get('content', '')[:100]
                    else:
                        # 尝试通用解析
                        item = card_content.get('item', {})
                        if isinstance(item, dict):
                            content = item.get('content', item.get('description', ''))[:100]
                        
                except Exception as e:
                    content = '[解析失败]'
                
                dynamics.append({
                    'dynamic_id': dynamic_id,
                    'type': dynamic_type,
                    'content': content,
                    'timestamp': timestamp,
                    'bvid': bvid,
                    'video_title': video_title
                })
        else:
            print(f"获取用户 {mid} 动态失败: {data.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"请求用户 {mid} 动态时出错: {e}")
    
    return dynamics


def search_user_by_keyword(keyword, header):
    """
    通過關鍵詞搜索用戶。
    
    Args:
        keyword: 搜索關鍵詞
        header: 請求頭
        
    Returns:
        [(mid, uname), ...] 列表
    """
    users = []
    url = "https://api.bilibili.com/x/web-interface/search/type"
    params = {
        'keyword': keyword,
        'search_type': 'bili_user',
        'page': 1
    }
    
    try:
        resp = requests.get(url, headers=header, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('code') == 0:
            result = data.get('data', {}).get('result', [])
            for item in result:
                mid = str(item.get('mid'))
                uname = item.get('uname')
                if mid and uname:
                    users.append((mid, uname))
        else:
            print(f"搜索用戶失敗: {data.get('message', '未知錯誤')}")
            
    except Exception as e:
        print(f"搜索用戶時出錯: {e}")
    
    return users
