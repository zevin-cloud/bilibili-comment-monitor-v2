from typing import List, Dict, Any, Optional


class CommentFilter:
    """评论过滤器 - 实现精准过滤"""
    
    def __init__(self):
        self.owner_only = True
        self.keywords = []
        self.min_length = 0
    
    def filter_by_owner(self, comments: List[Dict[str, Any]], owner_mid: str) -> List[Dict[str, Any]]:
        """
        只返回UP主本人的评论
        
        Args:
            comments: 评论列表
            owner_mid: UP主的MID
            
        Returns:
            过滤后的评论列表
        """
        filtered = []
        for comment in comments:
            comment_mid = str(comment.get('mid', ''))
            if comment_mid == owner_mid:
                comment['is_owner'] = True
                filtered.append(comment)
            else:
                comment['is_owner'] = False
        return filtered
    
    def filter_by_keywords(self, comments: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """
        按关键词过滤评论
        
        Args:
            comments: 评论列表
            keywords: 关键词列表
            
        Returns:
            包含任一关键词的评论列表
        """
        if not keywords:
            return comments
        
        filtered = []
        for comment in comments:
            message = comment.get('message', '').lower()
            if any(kw.lower() in message for kw in keywords):
                filtered.append(comment)
        return filtered
    
    def filter_by_min_length(self, comments: List[Dict[str, Any]], min_length: int) -> List[Dict[str, Any]]:
        """
        按最小长度过滤评论
        
        Args:
            comments: 评论列表
            min_length: 最小长度
            
        Returns:
            长度大于等于min_length的评论列表
        """
        if min_length <= 0:
            return comments
        
        return [c for c in comments if len(c.get('message', '')) >= min_length]
    
    def filter_high_priority(self, comments: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        分离高优先级（UP主本人）和普通评论
        
        Args:
            comments: 评论列表
            
        Returns:
            {
                'high_priority': [UP主本人的评论],
                'normal': [普通评论]
            }
        """
        result = {
            'high_priority': [],
            'normal': []
        }
        
        for comment in comments:
            if comment.get('is_owner', False):
                result['high_priority'].append(comment)
            else:
                result['normal'].append(comment)
        
        return result
    
    def apply_filters(self, comments: List[Dict[str, Any]], 
                    owner_mid: Optional[str] = None,
                    keywords: Optional[List[str]] = None,
                    min_length: int = 0) -> List[Dict[str, Any]]:
        """
        应用所有过滤条件
        
        Args:
            comments: 评论列表
            owner_mid: UP主的MID（如果提供，只返回UP主本人的评论）
            keywords: 关键词列表
            min_length: 最小长度
            
        Returns:
            过滤后的评论列表
        """
        filtered = comments.copy()
        
        if owner_mid:
            filtered = self.filter_by_owner(filtered, owner_mid)
        
        if keywords:
            filtered = self.filter_by_keywords(filtered, keywords)
        
        if min_length > 0:
            filtered = self.filter_by_min_length(filtered, min_length)
        
        return filtered
    
    def mark_owner_comments(self, comments: List[Dict[str, Any]], owner_mid: str) -> List[Dict[str, Any]]:
        """
        标记UP主本人的评论（不删除其他评论）
        
        Args:
            comments: 评论列表
            owner_mid: UP主的MID
            
        Returns:
            标记后的评论列表
        """
        for comment in comments:
            comment_mid = str(comment.get('mid', ''))
            comment['is_owner'] = (comment_mid == owner_mid)
        return comments
