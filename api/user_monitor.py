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


def fetch_dynamic_comments(dynamic_id, header, next_offset=0):
    """
    获取动态的评论列表。
    
    Args:
        dynamic_id: 动态ID
        header: 请求头
        next_offset: 分页偏移量
        
    Returns:
        {
            'comments': [{
                'rpid': 评论ID,
                'mid': 用户MID,
                'uname': 用户名,
                'message': 评论内容,
                'ctime': 发布时间
            }, ...],
            'next_offset': 下一页偏移量,
            'has_more': 是否还有更多
        }
    """
    comments = []
    has_more = False
    new_next_offset = 0
    
    # 只使用最基本的请求头，减少触发反爬虫的风险
    simple_header = {
        'User-Agent': header.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'),
        'Cookie': header.get('Cookie', ''),
        'Referer': f'https://t.bilibili.com/{dynamic_id}'
    }
    
    # 尝试使用评论主API（使用wbi）
    url = "https://api.bilibili.com/x/v2/reply/wbi/main"
    params = {
        'oid': dynamic_id,
        'type': 17,  # 动态评论类型
        'mode': 2,
        'pn': 1,
        'ps': 20,
        'sort': 2,
        'web_location': 1315875
    }
    
    try:
        print(f"尝试API {url}，参数: {params}")
        
        # 添加WBI签名
        img_key, sub_key = get_wbi_keys(simple_header)
        if img_key and sub_key:
            params = enc_wbi(params, img_key, sub_key)
            print(f"添加WBI签名后的参数: {params}")
        
        # 添加随机延迟，模拟真实用户行为
        time.sleep(1)
        
        resp = requests.get(url, headers=simple_header, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        print(f"API响应: {data}")
        
        if data.get('code') == 0:
            reply_data = data.get('data', {})
            # 检查不同的数据结构
            if 'replies' in reply_data:
                replies = reply_data['replies']
            elif 'list' in reply_data and 'replies' in reply_data['list']:
                replies = reply_data['list']['replies']
            else:
                replies = []
            
            for reply in replies:
                # 检查不同的评论数据结构
                if 'member' in reply and 'content' in reply:
                    member = reply['member']
                    content = reply['content']
                    comments.append({
                        'rpid': str(reply.get('rpid', '')),
                        'mid': str(member.get('mid', '')),
                        'uname': member.get('uname', ''),
                        'message': content.get('message', ''),
                        'ctime': reply.get('ctime', 0)
                    })
            
            # 检查是否还有更多评论
            if 'cursor' in reply_data:
                cursor = reply_data['cursor']
                has_more = cursor.get('is_end', True) == False
                new_next_offset = cursor.get('next_offset', 0)
            elif 'page' in reply_data:
                page = reply_data['page']
                has_more = page.get('pn', 1) < page.get('count', 1)
                new_next_offset = page.get('pn', 1) + 1
            
            print(f"成功获取到 {len(comments)} 条评论")
        else:
            print(f"API {url} 获取动态 {dynamic_id} 评论失败: {data.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"API {url} 请求动态 {dynamic_id} 评论时出错: {e}")
    
    # 如果第一个API失败，尝试使用动态评论专用API
    if not comments:
        url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_reply"
        params = {
            'dynamic_id': dynamic_id,
            'offset': next_offset,
            'size': 20
        }
        
        try:
            print(f"尝试API {url}，参数: {params}")
            
            # 添加随机延迟，模拟真实用户行为
            time.sleep(1)
            
            resp = requests.get(url, headers=simple_header, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            print(f"API响应: {data}")
            
            if data.get('code') == 0:
                reply_data = data.get('data', {})
                # 检查不同的数据结构
                if 'replies' in reply_data:
                    replies = reply_data['replies']
                elif 'list' in reply_data and 'replies' in reply_data['list']:
                    replies = reply_data['list']['replies']
                else:
                    replies = []
                
                for reply in replies:
                    # 检查不同的评论数据结构
                    if 'member' in reply and 'content' in reply:
                        member = reply['member']
                        content = reply['content']
                        comments.append({
                            'rpid': str(reply.get('rpid', '')),
                            'mid': str(member.get('mid', '')),
                            'uname': member.get('uname', ''),
                            'message': content.get('message', ''),
                            'ctime': reply.get('ctime', 0)
                        })
                
                # 检查是否还有更多评论
                if 'cursor' in reply_data:
                    cursor = reply_data['cursor']
                    has_more = cursor.get('is_end', True) == False
                    new_next_offset = cursor.get('next_offset', 0)
                
                print(f"成功获取到 {len(comments)} 条评论")
            else:
                print(f"API {url} 获取动态 {dynamic_id} 评论失败: {data.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"API {url} 请求动态 {dynamic_id} 评论时出错: {e}")
    
    # 如果无法获取评论，返回一个友好的错误信息
    if not comments:
        print(f"警告: 无法获取动态 {dynamic_id} 的评论，可能是因为API更改或反爬虫限制")
    
    return {
        'comments': comments,
        'next_offset': new_next_offset,
        'has_more': has_more
    }


def fetch_all_dynamic_comments(dynamic_id, header):
    """
    获取动态的所有评论。
    
    Args:
        dynamic_id: 动态ID
        header: 请求头
        
    Returns:
        [{
            'rpid': 评论ID,
            'mid': 用户MID,
            'uname': 用户名,
            'message': 评论内容,
            'ctime': 发布时间
        }, ...]
    """
    all_comments = []
    next_offset = 0
    
    while True:
        result = fetch_dynamic_comments(dynamic_id, header, next_offset)
        all_comments.extend(result['comments'])
        
        if not result['has_more'] or len(result['comments']) == 0:
            break
            
        next_offset = result['next_offset']
        time.sleep(0.5)  # 避免请求过快
    
    return all_comments
