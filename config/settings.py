from typing import List, Dict, Any


class Settings:
    """统一配置管理"""
    
    MONITOR_INTERVALS = {
        'peak': 30,
        'normal': 300,
        'night': 600
    }
    
    COMMENT_FILTER = {
        'owner_only': True,
        'keywords': [],
        'min_length': 0
    }
    
    NOTIFICATION = {
        'webhook_enabled': False,
        'webhook_url': '',
        'high_priority_only': False
    }
    
    DYNAMIC_MONITOR = {
        'enabled': True,
        'check_interval': 10,
        'max_activities_per_user': 5
    }
    
    @classmethod
    def get_monitor_interval(cls, schedule_name: str) -> int:
        """根据调度名称获取监控间隔"""
        return cls.MONITOR_INTERVALS.get(schedule_name, 300)
    
    @classmethod
    def set_owner_only(cls, value: bool):
        """设置是否只监控UP主本人的评论"""
        cls.COMMENT_FILTER['owner_only'] = value
    
    @classmethod
    def set_keywords(cls, keywords: List[str]):
        """设置关键词过滤"""
        cls.COMMENT_FILTER['keywords'] = keywords
    
    @classmethod
    def set_webhook_enabled(cls, enabled: bool):
        """设置Webhook通知是否启用"""
        cls.NOTIFICATION['webhook_enabled'] = enabled
    
    @classmethod
    def set_webhook_url(cls, url: str):
        """设置Webhook URL"""
        cls.NOTIFICATION['webhook_url'] = url
    
    @classmethod
    def set_high_priority_only(cls, value: bool):
        """设置是否只通知高优先级（UP主本人）评论"""
        cls.NOTIFICATION['high_priority_only'] = value
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'monitor_intervals': cls.MONITOR_INTERVALS,
            'comment_filter': cls.COMMENT_FILTER,
            'notification': cls.NOTIFICATION,
            'dynamic_monitor': cls.DYNAMIC_MONITOR
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典加载配置"""
        if 'monitor_intervals' in data:
            cls.MONITOR_INTERVALS.update(data['monitor_intervals'])
        if 'comment_filter' in data:
            cls.COMMENT_FILTER.update(data['comment_filter'])
        if 'notification' in data:
            cls.NOTIFICATION.update(data['notification'])
        if 'dynamic_monitor' in data:
            cls.DYNAMIC_MONITOR.update(data['dynamic_monitor'])
