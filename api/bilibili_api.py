import requests
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from .wbi_manager import WBIManager
from models import Activity, VideoActivity, DynamicActivity


class BilibiliAPI:
    """B站API统一封装"""
    
    def __init__(self, header: Dict[str, str]):
        self.header = header
        self.wbi_manager = WBIManager(header)
    
    def get_user_info(self, mid: str) -> Optional[Tuple[str, str]]:
        """
        通过用户ID获取用户信息
        
        Returns:
            (uname, face) 或 (None, None)
        """
        url = f"https://api.bilibili.com/x/web-interface/card?mid={mid}"
        try:
            resp = requests.get(url, headers=self.header, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if data.get('code') == 0:
                card = data.get('data', {}).get('card', {})
                uname = card.get('name')
                face = card.get('face')
                return uname, face
        except Exception as e:
            print(f"[API] 获取用户 {mid} 信息时出错: {e}")
        return None, None
    
    def get_user_dynamics(self, mid: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取用户的动态列表（包括文字、图片、视频等）
        
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
        
        header_copy = self.header.copy()
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
                    
                    content = ''
                    bvid = ''
                    video_title = ''
                    
                    try:
                        card_json = card.get('card')
                        if not card_json:
                            continue
                        card_content = json.loads(card_json)
                        
                        if dynamic_type == 8:
                            bvid = card_content.get('bvid', '')
                            video_title = card_content.get('title', '')
                            content = card_content.get('dynamic', '')[:100]
                        elif dynamic_type == 64:
                            article_title = card_content.get('title', '')
                            content = card_content.get('summary', '')[:100]
                            video_title = article_title
                        elif dynamic_type == 2:
                            item = card_content.get('item', {})
                            content = item.get('description', '')[:100]
                        elif dynamic_type == 4:
                            item = card_content.get('item', {})
                            content = item.get('content', '')[:100]
                        elif dynamic_type == 1:
                            item = card_content.get('item', {})
                            content = item.get('content', '')[:100]
                        else:
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
                print(f"[API] 获取用户 {mid} 动态失败: {data.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"[API] 请求用户 {mid} 动态时出错: {e}")
        
        return dynamics
    
    def get_user_dynamic_videos(self, mid: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        获取用户最新发布的视频（从动态中获取）
        
        Returns:
            [(bvid, title), ...] 列表
        """
        videos = []
        url = f"https://api.bilibili.com/x/space/wbi/arc/search"
        
        params = {
            'mid': mid,
            'ps': limit,
            'tid': 0,
            'pn': 1,
            'keyword': '',
            'order': 'pubdate',
            'platform': 'web',
            'web_location': '1550101',
            'order_avoided': 'true'
        }
        
        params = self.wbi_manager.sign(params)
        
        try:
            resp = requests.get(url, headers=self.header, params=params, timeout=10)
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
                print(f"[API] 获取用户 {mid} 视频列表失败: {data.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"[API] 请求用户 {mid} 视频列表时出错: {e}")
        
        return videos
    
    def get_video_info(self, bvid: str) -> Optional[Tuple[str, str, str]]:
        """
        通过BV号获取视频信息
        
        Returns:
            (oid, title, owner_mid) 或 (None, None, None)
        """
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        try:
            resp = requests.get(api_url, headers=self.header, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if data.get('code') == 0:
                video_data = data.get('data', {})
                oid = video_data.get('aid')
                title = video_data.get('title')
                owner_mid = str(video_data.get('owner', {}).get('mid', ''))
                if oid and title:
                    return str(oid), title.strip(), owner_mid
        except Exception as e:
            print(f"[API] 获取视频 {bvid} 信息时出错: {e}")
        return None, None, None
    
    def get_activity_comments(self, activity: Activity, next_offset: int = 0) -> Dict[str, Any]:
        """
        获取活动的评论列表
        
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
        
        url = activity.get_comment_api_url()
        params = activity.get_comment_api_params()
        
        if next_offset > 0:
            params['offset'] = next_offset
        
        params = self.wbi_manager.sign(params)
        
        try:
            full_url = f"{url}?{requests.compat.urlencode(params)}"
            resp = requests.get(full_url, headers=self.header, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('code') == 0:
                reply_data = data.get('data', {})
                
                if 'replies' in reply_data:
                    replies = reply_data['replies']
                elif 'list' in reply_data and 'replies' in reply_data['list']:
                    replies = reply_data['list']['replies']
                else:
                    replies = []
                
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
                
                if 'cursor' in reply_data:
                    cursor = reply_data['cursor']
                    has_more = cursor.get('is_end', True) == False
                    new_next_offset = cursor.get('next_offset', 0)
                elif 'page' in reply_data:
                    page = reply_data['page']
                    has_more = page.get('pn', 1) < page.get('count', 1)
                    new_next_offset = page.get('pn', 1) + 1
                else:
                    has_more = False
                    new_next_offset = 0
                
            else:
                error_msg = data.get('message', '未知错误')
                error_code = data.get('code')
                print(f"[API] 获取活动 {activity.id} 评论失败: 错误码={error_code}, 错误消息={error_msg}")
                
                comments = []
                has_more = False
                new_next_offset = 0
                
        except Exception as e:
            print(f"[API] 请求活动 {activity.id} 评论时出错: {e}")
        
        return {
            'comments': comments,
            'next_offset': new_next_offset,
            'has_more': has_more
        }
    
    def get_all_activity_comments(self, activity: Activity) -> List[Dict[str, Any]]:
        """
        获取活动的所有评论
        
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
            result = self.get_activity_comments(activity, next_offset)
            all_comments.extend(result['comments'])
            
            if not result['has_more'] or len(result['comments']) == 0:
                break
                
            next_offset = result['next_offset']
            time.sleep(0.5)
        
        return all_comments
    
    def search_user_by_keyword(self, keyword: str) -> List[Tuple[str, str]]:
        """
        通过关键词搜索用户
        
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
            resp = requests.get(url, headers=self.header, params=params, timeout=10)
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
                print(f"[API] 搜索用户失败: {data.get('message', '未知错误')}")
                
        except Exception as e:
            print(f"[API] 搜索用户时出错: {e}")
        
        return users
