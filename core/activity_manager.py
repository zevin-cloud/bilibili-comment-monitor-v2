from typing import List, Dict, Any, Optional, Set
import time
import database as db
import sqlite3
from api import BilibiliAPI
from models import Activity, VideoActivity, DynamicActivity
from .comment_filter import CommentFilter


class ActivityManager:
    """活动管理器 - 统一管理视频、动态、专栏等活动"""
    
    def __init__(self, api: BilibiliAPI):
        self.api = api
        self.comment_filter = CommentFilter()
    
    def check_user_activities(self, mid: str, uname: str) -> List[Activity]:
        """
        检查用户的新活动
        
        Args:
            mid: 用户MID
            uname: 用户名
            
        Returns:
            新活动列表
        """
        dynamics = self.api.get_user_dynamics(mid, limit=20)
        new_activities = []
        
        for dynamic in dynamics:
            dynamic_id = dynamic['dynamic_id']
            
            if self._is_new_activity(dynamic_id):
                activity = self._create_activity_from_dynamic(dynamic, mid, uname)
                if activity:
                    self._save_activity(activity)
                    new_activities.append(activity)
        
        return new_activities
    
    def _create_activity_from_dynamic(self, dynamic: Dict[str, Any], 
                                     mid: str, uname: str) -> Optional[Activity]:
        """从动态数据创建活动对象"""
        dynamic_type = dynamic['type']
        
        if dynamic_type == 8:
            return VideoActivity(
                bvid=dynamic.get('bvid', ''),
                oid=str(dynamic.get('oid', '')),
                title=dynamic.get('video_title', ''),
                owner_mid=mid,
                owner_name=uname,
                timestamp=dynamic.get('timestamp', 0)
            )
        elif dynamic_type in [2, 4]:
            return DynamicActivity(
                dynamic_id=dynamic['dynamic_id'],
                content=dynamic.get('content', ''),
                owner_mid=mid,
                owner_name=uname,
                dynamic_type=dynamic_type,
                timestamp=dynamic.get('timestamp', 0)
            )
        
        return None
    
    def _is_new_activity(self, activity_id: str) -> bool:
        """检查是否为新活动"""
        try:
            with sqlite3.connect(db.DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM activities WHERE id = ?
                ''', (activity_id,))
                return cursor.fetchone() is None
        except Exception as e:
            print(f"[ActivityManager] 检查活动 {activity_id} 时出错: {e}")
            return False
    
    def _save_activity(self, activity: Activity):
        """保存活动到数据库"""
        try:
            with sqlite3.connect(db.DB_NAME) as conn:
                cursor = conn.cursor()
                
                extra_data = {}
                if isinstance(activity, VideoActivity):
                    extra_data = {'bvid': activity.bvid}
                elif isinstance(activity, DynamicActivity):
                    extra_data = {'dynamic_type': activity.dynamic_type}
                
                import json
                cursor.execute('''
                    INSERT OR IGNORE INTO activities 
                    (id, activity_type, owner_mid, owner_name, content, title, extra_data, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    activity.id,
                    activity.type,
                    activity.owner_mid,
                    activity.owner_name,
                    activity.content,
                    activity.content if activity.type == Activity.ACTIVITY_TYPE_VIDEO else '',
                    json.dumps(extra_data),
                    activity.timestamp
                ))
                conn.commit()
        except Exception as e:
            print(f"[ActivityManager] 保存活动 {activity.id} 时出错: {e}")
    
    def check_activity_comments(self, activity: Activity, 
                              owner_only: bool = True) -> List[Dict[str, Any]]:
        """
        检查活动的评论
        
        Args:
            activity: 活动对象
            owner_only: 是否只返回UP主本人的评论
            
        Returns:
            新评论列表
        """
        comments = self.api.get_all_activity_comments(activity)
        
        if owner_only:
            comments = self.comment_filter.filter_by_owner(comments, activity.owner_mid)
        
        new_comments = self._filter_new_comments(comments, activity.id)
        
        return new_comments
    
    def _filter_new_comments(self, comments: List[Dict[str, Any]], 
                             activity_id: str) -> List[Dict[str, Any]]:
        """过滤出新评论"""
        new_comments = []
        
        try:
            with sqlite3.connect(db.DB_NAME) as conn:
                cursor = conn.cursor()
                
                for comment in comments:
                    rpid = comment['rpid']
                    cursor.execute('''
                        SELECT rpid FROM activity_comments 
                        WHERE rpid = ? AND activity_id = ?
                    ''', (rpid, activity_id))
                    
                    if cursor.fetchone() is None:
                        new_comments.append(comment)
                        cursor.execute('''
                            INSERT INTO activity_comments 
                            (rpid, activity_id, activity_type, commenter_mid, 
                             commenter_name, content, is_owner)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            rpid,
                            activity_id,
                            activity.type,
                            comment['mid'],
                            comment['uname'],
                            comment['message'],
                            1 if comment.get('is_owner', False) else 0
                        ))
                
                conn.commit()
        except Exception as e:
            print(f"[ActivityManager] 过滤新评论时出错: {e}")
        
        return new_comments
    
    def get_monitored_activities(self) -> List[Activity]:
        """获取所有监控的活动"""
        activities = []
        
        try:
            with sqlite3.connect(db.DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, activity_type, owner_mid, owner_name, 
                           content, title, extra_data, timestamp
                    FROM activities 
                    WHERE status = 'active'
                    ORDER BY timestamp DESC
                ''')
                
                for row in cursor.fetchall():
                    activity_id, activity_type, owner_mid, owner_name, \
                        content, title, extra_data, timestamp = row
                    
                    import json
                    extra = json.loads(extra_data) if extra_data else {}
                    
                    if activity_type == Activity.ACTIVITY_TYPE_VIDEO:
                        activity = VideoActivity(
                            bvid=extra.get('bvid', ''),
                            oid=activity_id,
                            title=title,
                            owner_mid=owner_mid,
                            owner_name=owner_name,
                            timestamp=timestamp
                        )
                    elif activity_type == Activity.ACTIVITY_TYPE_DYNAMIC:
                        activity = DynamicActivity(
                            dynamic_id=activity_id,
                            content=content,
                            owner_mid=owner_mid,
                            owner_name=owner_name,
                            dynamic_type=extra.get('dynamic_type', 0),
                            timestamp=timestamp
                        )
                    else:
                        continue
                    
                    activities.append(activity)
        except Exception as e:
            print(f"[ActivityManager] 获取监控活动时出错: {e}")
        
        return activities
    
    def remove_activity(self, activity_id: str) -> bool:
        """移除活动监控"""
        try:
            with sqlite3.connect(db.DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM activity_comments WHERE activity_id = ?
                ''', (activity_id,))
                cursor.execute('''
                    DELETE FROM activities WHERE id = ?
                ''', (activity_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ActivityManager] 移除活动 {activity_id} 时出错: {e}")
            return False
    
    def load_seen_comment_ids(self, activity_id: str) -> Set[str]:
        """加载已见评论ID"""
        try:
            with sqlite3.connect(db.DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT rpid FROM activity_comments WHERE activity_id = ?
                ''', (activity_id,))
                return {row[0] for row in cursor.fetchall()}
        except Exception as e:
            print(f"[ActivityManager] 加载已见评论ID时出错: {e}")
            return set()
