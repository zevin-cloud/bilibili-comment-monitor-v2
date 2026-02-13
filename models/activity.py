from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json


class Activity(ABC):
    """活动基类 - 统一表示视频、动态、专栏等活动"""
    
    ACTIVITY_TYPE_VIDEO = 'video'
    ACTIVITY_TYPE_DYNAMIC = 'dynamic'
    ACTIVITY_TYPE_ARTICLE = 'article'
    
    def __init__(self, activity_id: str, owner_mid: str, owner_name: str,
                 content: str, activity_type: str, timestamp: int = 0):
        self.id = activity_id
        self.owner_mid = owner_mid
        self.owner_name = owner_name
        self.content = content
        self.type = activity_type
        self.timestamp = timestamp
    
    @abstractmethod
    def get_comment_api_url(self) -> str:
        """获取评论API URL"""
        pass
    
    @abstractmethod
    def get_comment_api_params(self) -> Dict[str, Any]:
        """获取评论API参数"""
        pass
    
    @abstractmethod
    def get_activity_url(self) -> str:
        """获取活动页面URL"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'owner_mid': self.owner_mid,
            'owner_name': self.owner_name,
            'content': self.content,
            'type': self.type,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Activity':
        """从字典创建活动对象"""
        activity_type = data.get('type')
        if activity_type == cls.ACTIVITY_TYPE_VIDEO:
            return VideoActivity.from_dict(data)
        elif activity_type == cls.ACTIVITY_TYPE_DYNAMIC:
            return DynamicActivity.from_dict(data)
        elif activity_type == cls.ACTIVITY_TYPE_ARTICLE:
            return ArticleActivity.from_dict(data)
        return cls(**data)


class VideoActivity(Activity):
    """视频活动"""
    
    def __init__(self, bvid: str, oid: str, title: str, owner_mid: str,
                 owner_name: str, timestamp: int = 0):
        super().__init__(oid, owner_mid, owner_name, title,
                       self.ACTIVITY_TYPE_VIDEO, timestamp)
        self.bvid = bvid
        self.oid = oid
        self.title = title
    
    def get_comment_api_url(self) -> str:
        return "https://api.bilibili.com/x/v2/reply/wbi/main"
    
    def get_comment_api_params(self) -> Dict[str, Any]:
        return {
            'oid': self.oid,
            'type': 1,
            'mode': 2,
            'plat': 1,
            'web_location': 1315875,
            'pn': 1,
            'ps': 20
        }
    
    def get_activity_url(self) -> str:
        return f"https://www.bilibili.com/video/{self.bvid}"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'bvid': self.bvid,
            'oid': self.oid,
            'title': self.title
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoActivity':
        return cls(
            bvid=data['bvid'],
            oid=data['id'],
            title=data['title'],
            owner_mid=data['owner_mid'],
            owner_name=data['owner_name'],
            timestamp=data.get('timestamp', 0)
        )
    
    @classmethod
    def from_dynamic(cls, dynamic: Dict[str, Any]) -> 'VideoActivity':
        """从动态数据创建视频活动"""
        return cls(
            bvid=dynamic.get('bvid', ''),
            oid=str(dynamic.get('oid', '')),
            title=dynamic.get('title', ''),
            owner_mid=str(dynamic.get('owner_mid', '')),
            owner_name=dynamic.get('owner_name', ''),
            timestamp=dynamic.get('timestamp', 0)
        )


class DynamicActivity(Activity):
    """动态活动（图文、文字等）"""
    
    def __init__(self, dynamic_id: str, content: str, owner_mid: str,
                 owner_name: str, dynamic_type: int = 0, timestamp: int = 0):
        super().__init__(dynamic_id, owner_mid, owner_name, content,
                       self.ACTIVITY_TYPE_DYNAMIC, timestamp)
        self.dynamic_id = dynamic_id
        self.dynamic_type = dynamic_type
    
    def get_comment_api_url(self) -> str:
        return "https://api.bilibili.com/x/v2/reply/wbi/main"
    
    def get_comment_api_params(self) -> Dict[str, Any]:
        return {
            'oid': self.dynamic_id,
            'type': 17,
            'mode': 2,
            'web_location': 1315875
        }
    
    def get_activity_url(self) -> str:
        return f"https://t.bilibili.com/{self.dynamic_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'dynamic_id': self.dynamic_id,
            'dynamic_type': self.dynamic_type
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DynamicActivity':
        return cls(
            dynamic_id=data['id'],
            content=data['content'],
            owner_mid=data['owner_mid'],
            owner_name=data['owner_name'],
            dynamic_type=data.get('dynamic_type', 0),
            timestamp=data.get('timestamp', 0)
        )
    
    @classmethod
    def from_dynamic(cls, dynamic: Dict[str, Any]) -> 'DynamicActivity':
        """从动态数据创建动态活动"""
        return cls(
            dynamic_id=str(dynamic.get('dynamic_id', '')),
            content=dynamic.get('content', ''),
            owner_mid=str(dynamic.get('owner_mid', '')),
            owner_name=dynamic.get('owner_name', ''),
            dynamic_type=dynamic.get('type', 0),
            timestamp=dynamic.get('timestamp', 0)
        )


class ArticleActivity(Activity):
    """专栏活动"""
    
    def __init__(self, article_id: str, title: str, content: str,
                 owner_mid: str, owner_name: str, timestamp: int = 0):
        super().__init__(article_id, owner_mid, owner_name, content,
                       self.ACTIVITY_TYPE_ARTICLE, timestamp)
        self.article_id = article_id
        self.title = title
    
    def get_comment_api_url(self) -> str:
        return "https://api.bilibili.com/x/v2/reply/wbi/main"
    
    def get_comment_api_params(self) -> Dict[str, Any]:
        return {
            'oid': self.article_id,
            'type': 12,
            'mode': 2,
            'web_location': 1315875
        }
    
    def get_activity_url(self) -> str:
        return f"https://www.bilibili.com/read/cv{self.article_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'article_id': self.article_id,
            'title': self.title
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArticleActivity':
        return cls(
            article_id=data['id'],
            title=data['title'],
            content=data['content'],
            owner_mid=data['owner_mid'],
            owner_name=data['owner_name'],
            timestamp=data.get('timestamp', 0)
        )
