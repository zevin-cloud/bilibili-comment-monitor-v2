# 测试监控脚本
import sys
import time
import datetime
from main import get_header, get_information, fetch_latest_comments, process_and_notify_comment, fetch_all_sub_replies
import database as db

header = get_header()
print("Cookie验证成功")

# 获取视频
videos = db.get_monitored_videos()
print(f"\n数据库中的视频:")
for v in videos:
    print(f"  OID: {v[0]}, BV: {v[1]}, 标题: {v[2]}")

# 测试第一个视频
if videos:
    oid, bv_id, title = videos[0]
    print(f"\n测试视频: {title} (OID: {oid})")
    
    # 加载已见评论
    seen_ids = db.load_seen_comments_for_video(oid)
    print(f"已有 {len(seen_ids)} 条历史评论")
    
    # 获取最新评论
    print(f"\n获取最新评论...")
    comments = fetch_latest_comments(oid, header)
    print(f"获取到 {len(comments)} 条顶层评论")
    
    # 检查新评论
    new_count = 0
    for comment in comments:
        rpid = comment['rpid_str']
        member_mid = str(comment['member']['mid'])
        uname = comment['member']['uname']
        msg = comment['content']['message'][:30]
        
        if rpid not in seen_ids:
            new_count += 1
            print(f"  [新评论] {uname}: {msg}... (rpid: {rpid})")
        else:
            print(f"  [已记录] {uname}: {msg}...")
    
    print(f"\n发现 {new_count} 条新评论")
