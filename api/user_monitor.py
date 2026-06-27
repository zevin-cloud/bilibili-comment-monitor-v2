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
    """通過用戶ID獲取用戶信息。"""
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
    """獲取用戶最新發布的視頻（從動態中獲取）。"""
    videos = []
    url = f"https://api.bilibili.com/x/space/wbi/arc/search"
    mixin_key_salt = "ea1db124af3c7062474693fa704f4ff8"
    params = {
        'mid': mid,
        'ps': limit,
        'tid': 0,
        'pn': 1,
        'keyword': '',
        'order': 'pubdate',
        'platform': 'web',
        'web_location': '1550101',
        'order_avoided': 'true',
        'wts': int(time.time())
    }
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
    except Exception as e:
        print(f"請求用戶 {mid} 視頻列表時出錯: {e}")
    return videos


def extract_images_from_dynamic_item(item):
    images = []
    modules = item.get('modules', {})
    m_dyn = modules.get('module_dynamic', {})
    if m_dyn and m_dyn.get('major'):
        major = m_dyn['major']
        # 1. opus 类型 (新图文)
        if major.get('opus') and major['opus'].get('pics'):
            for pic in major['opus']['pics']:
                url = pic.get('url') or pic.get('src')
                if url:
                    images.append(url)
        # 2. draw 类型 (传统带图动态)
        elif major.get('draw') and major['draw'].get('items'):
            for pic in major['draw']['items']:
                url = pic.get('src') or pic.get('url')
                if url:
                    images.append(url)
        # 3. common 类型
        elif major.get('common') and major['common'].get('pics'):
            for pic in major['common']['pics']:
                url = pic.get('src') or pic.get('url')
                if url:
                    images.append(url)
        # 4. archive 视频封面类型
        elif major.get('archive') and major['archive'].get('cover'):
            cover_url = major['archive'].get('cover')
            if cover_url:
                images.append(cover_url)
    return images


def get_user_dynamics(mid, header, limit=20):
    """获取用户的动态列表（包括文字、图片、视频等）。支持充电专属动态。"""
    dynamics = []
    
    # 1. 获取普通动态
    url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={mid}&features=itemOpusStyle,listOnlyfans,opusBigCover&platform=web"
    type_map = {
        'DYNAMIC_TYPE_AV': 8,
        'DYNAMIC_TYPE_DRAW': 2,
        'DYNAMIC_TYPE_WORD': 4,
        'DYNAMIC_TYPE_FORWARD': 1,
        'DYNAMIC_TYPE_ARTICLE': 64,
        'DYNAMIC_TYPE_COMMON_VERTICAL': 2,
        'DYNAMIC_TYPE_MEDIALIST': 8,
    }
    
    try:
        resp = requests.get(url, headers=header, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') == 0:
            items = data.get('data', {}).get('items', [])
            for item in items:
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
                if m_dyn:
                    if m_dyn.get('desc') and m_dyn['desc'].get('text'):
                        content = m_dyn['desc']['text']
                    elif m_dyn.get('major') and m_dyn['major'].get('opus') and m_dyn['major']['opus'].get('summary'):
                        content = m_dyn['major']['opus']['summary'].get('text', '')
                if type_str == 'DYNAMIC_TYPE_AV' and m_dyn.get('major') and m_dyn['major'].get('archive'):
                    archive = m_dyn['major']['archive']
                    bvid = archive.get('bvid', '')
                    video_title = archive.get('title', '')
                    if not content: content = archive.get('desc', '')
                
                is_exclusive = item.get('basic', {}).get('is_only_fans', False)
                basic = item.get('basic', {})
                comment_oid = basic.get('comment_id_str')
                comment_type = basic.get('comment_type')
                
                # 如果是专属动态但内容为空，尝试获取详情
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
                            d_basic = d_item.get('basic', {})
                            comment_oid = d_basic.get('comment_id_str') or comment_oid
                            comment_type = d_basic.get('comment_type') or comment_type
                    except: pass

                images = extract_images_from_dynamic_item(item)
                dynamics.append({
                    'dynamic_id': id_str,
                    'type': dynamic_type,
                    'content': content,
                    'timestamp': timestamp,
                    'bvid': bvid,
                    'video_title': video_title,
                    'is_exclusive': is_exclusive,
                    'comment_oid': comment_oid,
                    'comment_type': comment_type,
                    'images': images
                })
    except Exception as e:
        print(f"请求用户 {mid} 普通动态时出错: {e}")

    # 按时间戳降序排序，并取前 limit 条
    dynamics.sort(key=lambda x: x['timestamp'], reverse=True)
    return dynamics[:limit]



def search_user_by_keyword(keyword, header):
    """通過關鍵詞搜索用戶。"""
    users = []
    url = "https://api.bilibili.com/x/web-interface/search/type"
    params = {'keyword': keyword, 'search_type': 'bili_user', 'page': 1}
    try:
        resp = requests.get(url, headers=header, params=params, timeout=10)
        data = resp.json()
        if data.get('code') == 0:
            result = data.get('data', {}).get('result', [])
            for item in result:
                mid = str(item.get('mid'))
                uname = item.get('uname')
                if mid and uname: users.append((mid, uname))
    except Exception as e:
        print(f"搜索用戶時出錯: {e}")
    return users


def fetch_dynamic_comments(dynamic_id, header, next_offset=0, oid=None, comment_type=None):
    """获取动态的评论列表。支持传入预先获取的 oid 和 comment_type。"""
    comments = []
    has_more = False
    new_next_offset = 0
    simple_header = {
        'User-Agent': header.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'),
        'Cookie': header.get('Cookie', ''),
        'Referer': f'https://t.bilibili.com/{dynamic_id}'
    }
    try:
        if not oid or not comment_type:
            detail_url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id={dynamic_id}"
            resp = requests.get(detail_url, headers=header, timeout=10)
            data = resp.json()
            if data.get('code') != 0: return {'comments': [], 'next_offset': 0, 'has_more': False}
            item = data.get('data', {}).get('item', {})
            basic = item.get('basic', {})
            oid = basic.get('comment_id_str')
            comment_type = basic.get('comment_type')
        if not oid or not comment_type: return {'comments': [], 'next_offset': 0, 'has_more': False}
        
        page = next_offset if next_offset > 0 else 1
        url = "https://api.bilibili.com/x/v2/reply"
        params = {'type': comment_type, 'oid': oid, 'pn': page, 'ps': 20, 'sort': 2}
        time.sleep(0.3)
        resp = requests.get(url, headers=simple_header, params=params, timeout=10)
        data = resp.json()
        if data.get('code') == 0:
            reply_data = data.get('data') or {}
            replies = reply_data.get('replies') or []
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
            page_info = reply_data.get('page') or {}
            current_page = page_info.get('pn', page)
            total_count = page_info.get('count', 0)
            page_size = page_info.get('size', 20)
            has_more = current_page * page_size < total_count
            new_next_offset = current_page + 1 if has_more else 0
    except Exception as e:
        print(f"请求动态 {dynamic_id} 评论时出错: {e}")
    return {'comments': comments, 'next_offset': new_next_offset, 'has_more': has_more}


def fetch_all_dynamic_comments(dynamic_id, header):
    """获取动态的所有评论。"""
    all_comments = []
    next_offset = 0
    while True:
        result = fetch_dynamic_comments(dynamic_id, header, next_offset)
        all_comments.extend(result['comments'])
        if not result['has_more'] or len(result['comments']) == 0: break
        next_offset = result['next_offset']
        time.sleep(0.5)
    return all_comments


def get_followed_feed(header, limit=20):
    """获取当前登录账号关注者的动态流（Feed All）。"""
    url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all?features=itemOpusStyle,listOnlyfans,opusBigCover&platform=web"
    type_map = {
        'DYNAMIC_TYPE_AV': 8, 'DYNAMIC_TYPE_DRAW': 2, 'DYNAMIC_TYPE_WORD': 4,
        'DYNAMIC_TYPE_FORWARD': 1, 'DYNAMIC_TYPE_ARTICLE': 64,
        'DYNAMIC_TYPE_COMMON_VERTICAL': 2, 'DYNAMIC_TYPE_MEDIALIST': 8,
    }
    results = []
    try:
        resp = requests.get(url, headers=header, timeout=10)
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
                basic = item.get('basic', {})
                images = extract_images_from_dynamic_item(item)
                results.append({
                    'mid': str(author.get('mid', '')),
                    'uname': author.get('name', ''),
                    'dynamic_id': item.get('id_str', ''),
                    'type': dynamic_type,
                    'content': content,
                    'timestamp': author.get('pub_ts', 0),
                    'is_exclusive': is_exclusive,
                    'comment_oid': basic.get('comment_id_str'),
                    'comment_type': basic.get('comment_type'),
                    'images': images
                })
    except Exception as e:
        print(f"获取关注动态流失败: {e}")
    return results
