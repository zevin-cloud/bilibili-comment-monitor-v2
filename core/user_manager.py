from typing import List, Tuple, Dict, Any, Optional
from config import database as db


class UserManager:
    """用户管理器 - 从视频中心转向用户中心"""
    
    def get_active_users(self) -> List[Tuple[str, str, bool, bool]]:
        """
        获取所有活跃监控用户
        
        Returns:
            [(mid, uname, monitor_comments, monitor_dynamic), ...]
        """
        return db.get_monitored_users()
    
    def get_comment_monitored_users(self) -> Dict[str, str]:
        """
        获取启用了评论监控的用户
        
        Returns:
            {mid: uname, ...}
        """
        users = db.get_monitored_users()
        return {u[0]: u[1] for u in users if u[2]}
    
    def get_dynamic_monitored_users(self) -> Dict[str, str]:
        """
        获取启用了动态监控的用户
        
        Returns:
            {mid: uname, ...}
        """
        users = db.get_monitored_users()
        return {u[0]: u[1] for u in users if u[3]}
    
    def add_user(self, mid: str, uname: str, 
                monitor_comments: bool = True, 
                monitor_dynamic: bool = True) -> bool:
        """
        添加监控用户
        
        Returns:
            是否添加成功
        """
        return db.add_monitored_user(
            mid, uname,
            1 if monitor_comments else 0,
            1 if monitor_dynamic else 0
        )
    
    def remove_user(self, mid: str) -> bool:
        """
        移除监控用户
        
        Returns:
            是否移除成功
        """
        return db.remove_monitored_user(mid)
    
    def update_user_settings(self, mid: str, 
                          monitor_comments: Optional[bool] = None,
                          monitor_dynamic: Optional[bool] = None) -> bool:
        """
        更新用户监控设置
        
        Returns:
            是否更新成功
        """
        return db.update_user_monitor_settings(
            mid,
            monitor_comments=1 if monitor_comments else 0 if monitor_comments is not None else None,
            monitor_dynamic=1 if monitor_dynamic else 0 if monitor_dynamic is not None else None
        )
    
    def update_user_last_activity(self, mid: str, activity_id: str):
        """
        更新用户最后处理的动态ID（断点续传）
        """
        try:
            with db.sqlite3.connect(db.DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE monitored_users 
                    SET last_activity_id = ?, last_check_time = CURRENT_TIMESTAMP
                    WHERE mid = ?
                ''', (activity_id, mid))
                conn.commit()
        except Exception as e:
            print(f"[UserManager] 更新用户 {mid} 最后活动ID时出错: {e}")
    
    def get_user_last_activity(self, mid: str) -> Optional[str]:
        """
        获取用户最后处理的动态ID
        
        Returns:
            最后活动ID或None
        """
        try:
            with db.sqlite3.connect(db.DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT last_activity_id FROM monitored_users WHERE mid = ?
                ''', (mid,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"[UserManager] 获取用户 {mid} 最后活动ID时出错: {e}")
            return None
    
    def get_user_info(self, mid: str) -> Optional[Tuple[str, str]]:
        """
        获取用户信息（从数据库）
        
        Returns:
            (mid, uname) 或 None
        """
        users = db.get_monitored_users()
        for user in users:
            if user[0] == mid:
                return (user[0], user[1])
        return None
