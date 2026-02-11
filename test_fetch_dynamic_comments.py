import requests
import time
import hashlib
import urllib.parse
import json
from main import get_header
import user_monitor

def test_dynamic_comments():
    """测试获取动态评论"""
    # 用户提供的opus链接
    dynamic_id = "1167989808986849345"
    
    # 获取请求头
    header = get_header()
    print(f"获取到请求头: {header}")
    
    # 调用修改后的fetch_dynamic_comments函数
    print(f"\n=== 测试获取动态 {dynamic_id} 的评论 ===")
    result = user_monitor.fetch_dynamic_comments(dynamic_id, header)
    
    print(f"\n获取评论结果:")
    print(f"评论数量: {len(result['comments'])}")
    print(f"是否有更多: {result['has_more']}")
    print(f"下一页偏移量: {result['next_offset']}")
    
    # 显示前3条评论
    print("\n前3条评论:")
    for i, comment in enumerate(result['comments'][:3]):
        print(f"评论 {i+1}:")
        print(f"  用户: {comment['uname']}")
        print(f"  内容: {comment['message']}")
        print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(comment['ctime']))}")
        print(f"  评论ID: {comment['rpid']}")

if __name__ == "__main__":
    test_dynamic_comments()
