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
    获取用户的动态列表（包括文字、图片、视频等）。支持充电专属动态。
    
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
            'video_title': 视频标题（如果是视频动态）,
            'is_exclusive': 是否为充电专属
        }, ...]
    """
    dynamics = []
    
    # 使用较新的 polymer API，支持充电动态
    url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={mid}"
    
    # 映射旧版类型ID以保持兼容性
    type_map = {
        'DYNAMIC_TYPE_AV': 8,
        'DYNAMIC_TYPE_DRAW': 2,
        'DYNAMIC_TYPE_WORD': 4,
        'DYNAMIC_TYPE_FORWARD': 1,
        'DYNAMIC_TYPE_ARTICLE': 64,
        'DYNAMIC_TYPE_COMMON_VERTICAL': 2, # 类似图片
        'DYNAMIC_TYPE_MEDIALIST': 8, # 播单，暂转为视频
    }
    
    try:
        resp = requests.get(url, headers=header, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('code') == 0:
            items = data.get('data', {}).get('items', [])
            
            for item in items[:limit]:
                id_str = item.get('id_str', '')
                type_str = item.get('type', '')
                dynamic_type = type_map.get(type_str, 0)
                
                modules = item.get('modules', {})
                author = modules.get('module_author', {})
                timestamp = author.get('pub_ts', 0)
                
                m_dyn = modules.get('module_dynamic', {})
                content = ''
                bvid = ''
                video_title = ''
                
                # 尝试多种路径获取文本内容
                if m_dyn:
                    # 1. 常见描述文本
                    if m_dyn.get('desc') and m_dyn['desc'].get('text'):
                        content = m_dyn['desc']['text']
                    # 2. 新版 Opus 格式
                    elif m_dyn.get('major') and m_dyn['major'].get('opus') and m_dyn['major']['opus'].get('summary'):
                        content = m_dyn['major']['opus']['summary'].get('text', '')
                    # 3. 转发动态内容
                    elif type_str == 'DYNAMIC_TYPE_FORWARD' and m_dyn.get('desc'):
                        content = m_dyn['desc'].get('text', '')
                
                # 针对视频类型的特殊处理
                if type_str == 'DYNAMIC_TYPE_AV' and m_dyn.get('major') and m_dyn['major'].get('archive'):
                    archive = m_dyn['major']['archive']
                    bvid = archive.get('bvid', '')
                    video_title = archive.get('title', '')
                    if not content:
                        content = archive.get('desc', '')
                
                # 检查是否为充电专属
                is_exclusive = item.get('basic', {}).get('is_only_fans', False)
                
                # 如果是充电动态且内容为空，尝试通过详情接口获取（有时feed接口返回null）
                if is_exclusive and not content:
                    try:
                        detail_url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id={id_str}"
                        d_resp = requests.get(detail_url, headers=header, timeout=5)
                        d_data = d_resp.json()
                        if d_data.get('code') == 0:
                            d_item = d_data.get('data', {}).get('item', {})
                            dm_dyn = d_item.get('modules', {}).get('module_dynamic', {})
                            if dm_dyn:
                                if dm_dyn.get('desc') and dm_dyn['desc'].get('text'):
                                    content = dm_dyn['desc']['text']
                                elif dm_dyn.get('major') and dm_dyn['major'].get('opus') and dm_dyn['major']['opus'].get('summary'):
                                    content = dm_dyn['major']['opus']['summary'].get('text', '')
                    except:
                        pass

                dynamics.append({
                    'dynamic_id': id_str,
                    'type': dynamic_type,
                    'content': content,
                    'timestamp': timestamp,
                    'bvid': bvid,
                    'video_title': video_title,
                    'is_exclusive': is_exclusive
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
        next_offset: 分页偏移量（页码）
        
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
    
    simple_header = {
        'User-Agent': header.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'),
        'Cookie': header.get('Cookie', ''),
        'Referer': f'https://t.bilibili.com/{dynamic_id}'
    }
    
    try:
        url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail"
        params = {'dynamic_id': dynamic_id}
        resp = requests.get(url, headers=simple_header, params=params, timeout=10)
        data = resp.json()
        
        if data.get('code') != 0:
            print(f"获取动态详情失败: {data.get('message', '未知错误')}")
            return {'comments': [], 'next_offset': 0, 'has_more': False}
        
        card = data.get('data', {}).get('card', {})
        card_data = json.loads(card) if isinstance(card, str) else card
        desc = card_data.get('desc', {})
        
        dynamic_type = desc.get('type', 0)
        comment_count = desc.get('comment', 0)
        
        comment_type = 11
        oid = ''
        
        if dynamic_type == 8:
            comment_type = 1
            oid = desc.get('rid_str', desc.get('rid', ''))
            if not oid:
                stat = card_data.get('stat', {})
                oid = stat.get('aid', '')
            print(f"视频动态 {dynamic_id} - 使用视频评论接口 type=1, aid={oid}")
        else:
            comment_type = 11
            oid = desc.get('rid_str', desc.get('rid', ''))
            print(f"图文/文字动态 {dynamic_id} - 使用动态评论接口 type=11, rid={oid}")
        
        if not oid:
            print(f"动态 {dynamic_id} 没有找到评论OID")
            return {'comments': [], 'next_offset': 0, 'has_more': False}
        
        print(f"动态 {dynamic_id} 评论数: {comment_count}, OID: {oid}, 评论类型: {comment_type}")
        
        page = next_offset if next_offset > 0 else 1
        url = "https://api.bilibili.com/x/v2/reply"
        params = {
            'type': comment_type,
            'oid': oid,
            'pn': page,
            'ps': 20,
            'sort': 2
        }
        
        time.sleep(0.5)
        
        resp = requests.get(url, headers=simple_header, params=params, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            reply_data = data.get('data', {})
            replies = reply_data.get('replies', [])
            
            for reply in replies:
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
            
            page_info = reply_data.get('page', {})
            current_page = page_info.get('pn', page)
            total_count = page_info.get('count', 0)
            page_size = page_info.get('size', 20)
            
            has_more = current_page * page_size < total_count
            new_next_offset = current_page + 1 if has_more else 0
            
            print(f"成功获取到 {len(comments)} 条评论 (第{current_page}页, 共{total_count}条)")
        else:
            print(f"获取评论失败: {data.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"请求动态 {dynamic_id} 评论时出错: {e}")
    
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

def get_followed_feed(header, limit=20):
    """
    获取当前登录账号关注者的动态流（Feed All）。
    包含充电专属动态，比空间接口更全面。
    
    Args:
        header: 请求头
        limit: 限制数量
        
    Returns:
        [{
            'mid': 发布者ID,
            'uname': 发布者名字,
            'dynamic_id': 动态ID,
            'type': 动态类型,
            'content': 内容,
            'timestamp': 时间戳,
            'is_exclusive': 是否专属
        }, ...]
    """
    url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all"
    
    type_map = {
        'DYNAMIC_TYPE_AV': 8,
        'DYNAMIC_TYPE_DRAW': 2,
        'DYNAMIC_TYPE_WORD': 4,
        'DYNAMIC_TYPE_FORWARD': 1,
        'DYNAMIC_TYPE_ARTICLE': 64,
        'DYNAMIC_TYPE_COMMON_VERTICAL': 2,
        'DYNAMIC_TYPE_MEDIALIST': 8,
    }
    
    results = []
    try:
        resp = requests.get(url, headers=header, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('code') == 0:
            items = data.get('data', {}).get('items', [])
            for item in items[:limit]:
                modules = item.get('modules', {})
                author = modules.get('module_author', {})
                
                type_str = item.get('type', '')
                dynamic_type = type_map.get(type_str, 0)
                
                m_dyn = modules.get('module_dynamic', {})
                content = ''
                if m_dyn:
                    if m_dyn.get('desc') and m_dyn['desc'].get('text'):
                        content = m_dyn['desc']['text']
                    elif m_dyn.get('major') and m_dyn['major'].get('opus') and m_dyn['major']['opus'].get('summary'):
                        content = m_dyn['major']['opus']['summary'].get('text', '')
                
                is_exclusive = item.get('basic', {}).get('is_only_fans', False)
                
                results.append({
                    'mid': str(author.get('mid', '')),
                    'uname': author.get('name', ''),
                    'dynamic_id': item.get('id_str', ''),
                    'type': dynamic_type,
                    'content': content,
                    'timestamp': author.get('pub_ts', 0),
                    'is_exclusive': is_exclusive
                })
    except Exception as e:
        print(f"获取关注动态流失败: {e}")
        
    return results
