# filename: auto_monitor.py
"""自动监控脚本 - 无需交互，直接开始监控"""
import sys
import time
import datetime
import subprocess
from main import get_header, get_information, fetch_latest_comments, process_and_notify_comment, fetch_all_sub_replies
import database as db
import notifier
import bvget
import user_monitor

# 导入平台相关模块
import platform
if platform.system() == "Windows":
    import msvcrt
else:
    import select

def log(message):
    """打印并记录日志"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 移除emoji避免编码问题
    message = message.encode('gbk', errors='ignore').decode('gbk')
    log_line = f"{timestamp} - {message}"
    print(log_line)
    # 同时写入日志文件
    with open('bilibili_monitor.log', 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')

def check_video_comments(oid, bv_id, title, header, seen_ids, filter_user_mids=None):
    """检查单个视频的评论"""
    new_comments_found = []
    
    try:
        latest_comments = fetch_latest_comments(oid, header)
        if not latest_comments:
            return False, []
        
        for comment in latest_comments:
            commenter_mid = str(comment['member']['mid'])
            
            # 检查是否被过滤
            if filter_user_mids and commenter_mid not in filter_user_mids:
                pass
            else:
                new_main_comment = process_and_notify_comment(comment, oid, seen_ids, 
                                                               filter_user_mids=filter_user_mids)
                if new_main_comment:
                    new_comments_found.append(new_main_comment)
            
            # 检查子评论
            if comment.get('replies'):
                for sub_reply in comment['replies']:
                    new_sub_comment = process_and_notify_comment(sub_reply, oid, seen_ids,
                                                                 parent_user_name=comment['member']['uname'],
                                                                 filter_user_mids=filter_user_mids)
                    if new_sub_comment:
                        new_comments_found.append(new_sub_comment)
            
            # 获取更多子评论
            rcount = comment.get('rcount', 0)
            initial_reply_count = len(comment.get('replies') or [])
            
            if rcount > initial_reply_count:
                all_sub_replies = fetch_all_sub_replies(oid, comment['rpid_str'], header)
                for sub_reply in all_sub_replies:
                    new_hidden_comment = process_and_notify_comment(sub_reply, oid, seen_ids,
                                                                    parent_user_name=comment['member']['uname'],
                                                                    filter_user_mids=filter_user_mids)
                    if new_hidden_comment:
                        new_comments_found.append(new_hidden_comment)
        
        return len(new_comments_found) > 0, new_comments_found
    except Exception as e:
        log(f"检查视频 {title} 时出错: {e}")
        return False, []

def auto_monitor():
    """自动监控所有配置的视频和用户"""
    log("=" * 50)
    log("B站评论自动监控系统启动")
    log("=" * 50)
    
    # 获取请求头
    try:
        header = get_header()
        log("✅ Cookie验证成功")
    except Exception as e:
        log(f"❌ Cookie验证失败: {e}")
        sys.exit(1)
    
    # 获取所有监控的视频
    videos = db.get_monitored_videos()
    if not videos:
        log("⚠️ 数据库中没有视频，尝试从用户动态获取...")
    else:
        log(f"📹 数据库中有 {len(videos)} 个视频")
    
    # 获取启用了动态监控的用户
    dynamic_users = db.get_dynamic_monitored_user_mids()
    if dynamic_users:
        log(f"[用户] 有 {len(dynamic_users)} 个用户启用了动态监控")
        
        # 获取并显示用户名
        for mid in list(dynamic_users.keys()):
            uname, _ = user_monitor.get_user_info(mid, header)
            if uname:
                dynamic_users[mid] = uname
                log(f"[用户] {mid} -> {uname}")
    
    # 自动添加用户动态视频
    if dynamic_users:
        log("[动态] 检查用户动态视频...")
        existing_bvids = db.get_dynamic_video_bvids()
        added_count = 0
        
        for mid, uname in dynamic_users.items():
            try:
                videos_list = user_monitor.get_user_dynamic_videos(mid, header, limit=10)
                for bvid, title in videos_list:
                    if bvid not in existing_bvids:
                        oid, video_title = get_information(bvid, header)
                        if oid and video_title:
                            if db.add_video_to_db(oid, bvid, video_title):
                                db.add_dynamic_video(bvid, mid, video_title)
                                log(f"[添加] 从 [{uname}] 动态添加视频: {video_title}")
                                added_count += 1
                                time.sleep(0.5)
            except Exception as e:
                log(f"[错误] 检查用户 {uname} 视频时出错: {e}")
        
        if added_count > 0:
            log(f"[完成] 从动态添加了 {added_count} 个新视频")
        
        # 检查用户动态（文字、图片等）
        log("[动态] 检查用户动态内容...")
        for mid, uname in dynamic_users.items():
            try:
                dynamics = user_monitor.get_user_dynamics(mid, header, limit=10)
                if dynamics:
                    log(f"[动态] 用户 [{uname}] 有 {len(dynamics)} 条动态:")
                    for dyn in dynamics:
                        type_name = {
                            1: "转发",
                            2: "图片",
                            4: "文字",
                            8: "视频",
                            64: "专栏"
                        }.get(dyn['type'], f"类型{dyn['type']}")
                        
                        if dyn['bvid']:
                            log(f"  [{type_name}] {dyn['video_title']}")
                        else:
                            content = dyn['content'][:50] if dyn['content'] else '[无内容]'
                            log(f"  [{type_name}] {content}...")
            except Exception as e:
                log(f"[错误] 检查用户 {uname} 动态时出错: {e}")
    
    # 重新获取视频列表
    videos = db.get_monitored_videos()
    if not videos:
        log("❌ 没有视频可监控，请先添加视频或用户")
        sys.exit(1)
    
    log(f"🎯 开始监控 {len(videos)} 个视频")
    for v in videos:
        log(f"   - {v[2]} ({v[1]})")
    
    # 获取监控间隔
    interval, schedule_name = db.get_current_interval()
    log(f"⏰ 当前监控频率: {schedule_name} ({interval}秒)")
    
    # 初始化Webhook
    webhook_enabled = notifier.check_webhook_configured()
    if webhook_enabled:
        log("[通知] Webhook通知已启用")
    
    # 初始化视频监控数据
    video_targets = {}
    total_seen = 0
    for oid, bv_id, title in videos:
        video_targets[oid] = {
            "title": title,
            "bv_id": bv_id,
            "seen_ids": db.load_seen_comments_for_video(oid)
        }
        seen_count = len(video_targets[oid]['seen_ids'])
        total_seen += seen_count
    
    log(f"✅ 准备就绪！共 {total_seen} 条历史评论")
    log("=" * 50)
    
    # 获取评论监控用户过滤
    filter_user_mids = db.get_comment_monitored_user_mids()
    if filter_user_mids:
        log(f"🎯 只监控 {len(filter_user_mids)} 个指定用户的评论")
    
    # 开始监控循环
    loop_count = 0
    try:
        while True:
            loop_count += 1
            log(f"\n🔄 第 {loop_count} 轮监控开始")
            
            # 重新获取视频列表（可能有新视频）
            current_videos = db.get_monitored_videos()
            current_oids = {v[0] for v in current_videos}
            
            # 添加新视频到监控
            for oid, bv_id, title in current_videos:
                if oid not in video_targets:
                    video_targets[oid] = {
                        "title": title,
                        "bv_id": bv_id,
                        "seen_ids": db.load_seen_comments_for_video(oid)
                    }
                    log(f"➕ 新视频加入监控: {title}")
            
            round_new = 0
            for oid, data in video_targets.items():
                if oid not in current_oids:
                    continue  # 跳过已删除的视频
                    
                title = data['title']
                seen_ids = data['seen_ids']
                
                try:
                    has_new, new_comments = check_video_comments(
                        oid, data['bv_id'], title, header, seen_ids, filter_user_mids
                    )
                    
                    if has_new:
                        log(f"[新评论] 【{title}】发现 {len(new_comments)} 则新评论！")
                        for c in new_comments:
                            log(f"   [{c['type']}] {c['user']}: {c['message'][:50]}...")
                        
                        if webhook_enabled:
                            notifier.send_webhook_notification(title, new_comments)
                    else:
                        log(f"[检查] 【{title}】无新评论")
                    
                    time.sleep(1)  # 避免请求过快
                except Exception as e:
                    log(f"⚠️ 检查视频 {title} 时出错: {e}")
            
            # 检查是否需要更新监控间隔
            current_interval, current_schedule = db.get_current_interval()
            if current_interval != interval:
                interval = current_interval
                log(f"⏰ 监控频率已更新: {current_schedule} ({interval}秒)")
            
            log(f"✅ 第 {loop_count} 轮监控完成，{interval}秒后继续...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        log("\n👋 监控已停止")
    except Exception as e:
        log(f"❌ 监控出错: {e}")
        raise

if __name__ == "__main__":
    auto_monitor()
