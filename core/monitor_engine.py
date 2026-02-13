from typing import Dict, List, Any, Optional, Callable
import time
import datetime
import pandas as pd
import platform
import sys

if platform.system() == "Windows":
    import msvcrt
else:
    import select

from api import BilibiliAPI
from .user_manager import UserManager
from .activity_manager import ActivityManager
from .comment_filter import CommentFilter
from models import Activity, VideoActivity
from config import database as db
from core import notifier


class MonitorEngine:
    """监控引擎 - 用户驱动的核心调度器"""
    
    def __init__(self, header: Dict[str, str], log_func: Optional[Callable] = None):
        self.header = header
        self.api = BilibiliAPI(header)
        self.user_manager = UserManager()
        self.activity_manager = ActivityManager(self.api)
        self.comment_filter = CommentFilter()
        
        self.monitored_activities: Dict[str, Dict[str, Any]] = {}
        self.webhook_enabled = False
        self.owner_only = True
        self.enable_dynamic_monitor = True
        
        self.check_count = 0
        self.total_new_comments = 0
        self.log = log_func if log_func else print
    
    def initialize(self, webhook_enabled: bool = False, 
                  owner_only: bool = True,
                  enable_dynamic_monitor: bool = True):
        """初始化监控引擎"""
        self.webhook_enabled = webhook_enabled
        self.owner_only = owner_only
        self.enable_dynamic_monitor = enable_dynamic_monitor
        
        self.log("\n" + "=" * 20 + " 初始化监控数据 " + "=" * 20)
        
        activities = self.activity_manager.get_monitored_activities()
        total_seen = 0
        
        for activity in activities:
            seen_ids = self.activity_manager.load_seen_comment_ids(activity.id)
            self.monitored_activities[activity.id] = {
                'activity': activity,
                'seen_ids': seen_ids
            }
            seen_count = len(seen_ids)
            total_seen += seen_count
            
            activity_title = activity.content if activity.type == Activity.ACTIVITY_TYPE_DYNAMIC else activity.content
            self.log(f"正在为【{activity_title}】加载历史评论记录...")
            self.log(f"-> 加载完成，已记录 {seen_count} 条历史评论。")
        
        import database as db
        videos = db.get_monitored_videos()
        for oid, bv_id, title, owner_mid in videos:
            video_activity = VideoActivity(
                bvid=bv_id,
                oid=str(oid),
                title=title,
                owner_mid=str(owner_mid),
                owner_name='',
                timestamp=0
            )
            seen_ids = self.activity_manager.load_seen_comment_ids(str(oid))
            self.monitored_activities[str(oid)] = {
                'activity': video_activity,
                'seen_ids': seen_ids
            }
            seen_count = len(seen_ids)
            total_seen += seen_count
            
            self.log(f"正在为【{title}】加载历史评论记录...")
            self.log(f"-> 加载完成，已记录 {seen_count} 条历史评论。")
        
        self.log(f"\n✅ 准备就绪！开始监控 {len(self.monitored_activities)} 个活动，共 {total_seen} 条历史评论。")
        self.log("=" * 55)
    
    def run_monitoring_loop(self):
        """主监控循环"""
        while True:
            try:
                self.check_count += 1
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.log(f"\n[{now}] 第 {self.check_count} 轮检查开始...")
                
                if self.enable_dynamic_monitor:
                    self._check_user_dynamics()
                
                round_new_comments = self._check_activity_comments()
                
                self._print_statistics(round_new_comments)
                
                interval, schedule_name = db.get_current_interval()
                self.log(f"   - 当前时间段: {schedule_name} ({interval}秒)")
                
                self._wait_with_manual_trigger(interval)
                
            except KeyboardInterrupt:
                self.log("\n程序被用户手动中断 (Ctrl+C)。再见！")
                break
            except Exception as e:
                self.log(f"\n[严重错误] 监控循环中发生未知错误 ({type(e).__name__}): {e}")
                self.log("等待 60 秒后重试...")
                time.sleep(60)
    
    def _check_user_dynamics(self):
        """检查用户的新动态"""
        dynamic_users = self.user_manager.get_dynamic_monitored_users()
        
        if not dynamic_users:
            self.log("  -> [动态监控] 没有设置动态监控的用户")
            return
        
        self.log(f"  -> [动态监控] 正在检查 {len(dynamic_users)} 个用户的最新动态...")
        self.log(f"     用户列表: {', '.join(dynamic_users.values())}")
        
        total_new_activities = 0
        
        for mid, uname in dynamic_users.items():
            try:
                new_activities = self.activity_manager.check_user_activities(mid, uname)
                
                if new_activities:
                    total_new_activities += len(new_activities)
                    
                    for activity in new_activities:
                        self.monitored_activities[activity.id] = {
                            'activity': activity,
                            'seen_ids': set()
                        }
                        
                        activity_title = activity.content if activity.type == Activity.ACTIVITY_TYPE_DYNAMIC else activity.content
                        self.log(f"     ✚ 从 [{uname}] 的动态添加新活动: 【{activity_title}】")
                        
                        time.sleep(0.5)
                    
                    self.log(f"     🗑️  删除用户 [{uname}] 的旧动态监控，只保留最新动态")
                    self._remove_old_user_activities(mid, new_activities[0].id)
                else:
                    self.log(f"     • 用户 [{uname}] 暂无新动态")
                    
            except Exception as e:
                self.log(f"     ✗ 检查用户 [{uname}] 动态时出错: {e}")
        
        if total_new_activities > 0:
            self.log(f"  -> [动态监控] 共添加 {total_new_activities} 个新活动到监控列表")
        else:
            self.log(f"  -> [动态监控] 暂无新活动")
    
    def _remove_old_user_activities(self, mid: str, keep_activity_id: str):
        """删除用户的所有旧活动监控，只保留指定的活动"""
        try:
            import sqlite3
            with sqlite3.connect(db.DB_NAME) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id FROM activities 
                    WHERE owner_mid = ? AND id != ? AND activity_type IN ('dynamic', 'video', 'article')
                ''', (mid, keep_activity_id))
                
                old_activities = cursor.fetchall()
                
                for (activity_id,) in old_activities:
                    self.log(f"        - 删除旧活动: {activity_id}")
                    
                    if activity_id in self.monitored_activities:
                        del self.monitored_activities[activity_id]
                    
                    cursor.execute('DELETE FROM activity_comments WHERE activity_id = ?', (activity_id,))
                    cursor.execute('DELETE FROM activities WHERE id = ?', (activity_id,))
                
                conn.commit()
                
        except Exception as e:
            self.log(f"        ✗ 删除旧活动时出错: {e}")
    
    def _check_activity_comments(self) -> int:
        """检查所有活动的评论"""
        round_new_comments = 0
        
        for activity_id, data in self.monitored_activities.items():
            activity = data['activity']
            seen_ids = data['seen_ids']
            
            activity_title = activity.content if activity.type == Activity.ACTIVITY_TYPE_DYNAMIC else activity.content
            self.log(f"  -> [评论监控] 正在检查【{activity_title}】...")
            
            try:
                new_comments = self.activity_manager.check_activity_comments(
                    activity, owner_only=self.owner_only
                )
                
                if new_comments:
                    round_new_comments += len(new_comments)
                    self.total_new_comments += len(new_comments)
                    
                    formatted_comments = self._format_comments(new_comments)
                    
                    self.log("*" * 25)
                    self.log(f"🔥【{activity_title}】发现 {len(formatted_comments)} 条新评论！")
                    self.log("*" * 25)
                    
                    for comment in formatted_comments:
                        self.log(f"  类型: {comment['type']}")
                        self.log(f"  用户: {comment['user']}")
                        self.log(f"  评论: {comment['message']}")
                        self.log(f"  时间: {comment['time'].strftime('%Y-%m-%d %H:%M:%S')}")
                        self.log("-" * 25)
                    
                    if self.webhook_enabled:
                        notifier.send_webhook_notification(activity_title, formatted_comments)
                else:
                    self.log(f"     ✓ 暂无新评论")
                
                time.sleep(1)
                
            except Exception as e:
                self.log(f"     ✗ 检查活动【{activity_title}】时出错: {e}")
        
        return round_new_comments
    
    def _format_comments(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化评论"""
        formatted = []
        
        for comment in comments:
            formatted.append({
                "user": comment['uname'],
                "message": comment['message'],
                "time": pd.to_datetime(comment["ctime"], unit='s', utc=True).tz_convert('Asia/Shanghai'),
                "type": "UP主评论" if comment.get('is_owner', False) else "评论"
            })
        
        return sorted(formatted, key=lambda x: x['time'])
    
    def _print_statistics(self, round_new_comments: int):
        """打印统计信息"""
        self.log(f"\n📊 第 {self.check_count} 轮检查完成统计:")
        self.log(f"   - 监控活动数: {len(self.monitored_activities)}")
        self.log(f"   - 本轮新评论: {round_new_comments}")
        self.log(f"   - 总新评论数: {self.total_new_comments}")
    
    def _wait_with_manual_trigger(self, interval_seconds: int):
        """等待指定的秒数，同时监听用户的 Enter 键以立即触发"""
        minutes = interval_seconds // 60
        seconds = interval_seconds % 60
        wait_message = f"等待 {minutes} 分钟 {seconds} 秒后" if minutes > 0 else f"等待 {seconds} 秒后"
        
        self.log(f"\n所有活动检查完毕。{wait_message}进行下一轮检查...")
        
        start_time = time.time()
        while time.time() - start_time < interval_seconds:
            if platform.system() == "Windows":
                try:
                    if msvcrt.kbhit():
                        if msvcrt.getch() in [b'\r', b'\n']:
                            self.log("\n收到手动触发指令，立即开始新一轮检查！")
                            return
                except:
                    pass
            else:
                try:
                    readable, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if readable:
                        sys.stdin.readline()
                        self.log("\n收到手动触发指令，立即开始新一轮检查！")
                        return
                except (OSError, ValueError):
                    pass
            
            time.sleep(0.1)
    
    def add_activity(self, activity: Activity):
        """手动添加活动到监控"""
        self.monitored_activities[activity.id] = {
            'activity': activity,
            'seen_ids': set()
        }
        self.activity_manager._save_activity(activity)
        print(f"✅ 已添加活动【{activity.content}】到监控列表")
    
    def remove_activity(self, activity_id: str):
        """从监控中移除活动"""
        if activity_id in self.monitored_activities:
            del self.monitored_activities[activity_id]
        self.activity_manager.remove_activity(activity_id)
        print(f"✅ 已从监控列表移除活动 {activity_id}")
