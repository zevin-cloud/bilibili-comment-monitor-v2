from typing import Tuple
import datetime
import database as db


class Scheduler:
    """调度管理器 - 管理监控时间段和间隔"""
    
    def __init__(self):
        self.current_interval = 300
        self.current_schedule_name = '默认(5分钟)'
    
    def get_current_interval(self) -> Tuple[int, str]:
        """
        根据当前时间获取应该的监控间隔（秒）
        
        Returns:
            (interval_seconds, schedule_name)
        """
        interval, name = db.get_current_interval()
        self.current_interval = interval
        self.current_schedule_name = name
        return interval, name
    
    def get_all_schedules(self):
        """获取所有监控时间段配置"""
        return db.get_monitor_schedules()
    
    def add_schedule(self, name: str, start_time: str, end_time: str,
                    days_of_week: str, interval_seconds: int) -> bool:
        """添加新的监控时间段配置"""
        return db.add_monitor_schedule(name, start_time, end_time, days_of_week, interval_seconds)
    
    def update_schedule(self, schedule_id: int, **kwargs) -> bool:
        """更新监控时间段配置"""
        return db.update_monitor_schedule(schedule_id, **kwargs)
    
    def delete_schedule(self, schedule_id: int) -> bool:
        """删除监控时间段配置"""
        return db.delete_monitor_schedule(schedule_id)
    
    def is_peak_time(self) -> bool:
        """判断当前是否为高峰时段"""
        interval, name = self.get_current_interval()
        return interval < 60
    
    def get_schedule_info(self) -> dict:
        """获取当前调度信息"""
        return {
            'interval': self.current_interval,
            'schedule_name': self.current_schedule_name,
            'is_peak': self.is_peak_time()
        }
