# filename: auto_monitor.py
"""自动监控脚本 - 无需交互，直接开始监控"""
import sys
import time
import datetime
from main import get_header, get_information, fetch_latest_comments, process_and_notify_comment, fetch_all_sub_replies
import database as db
import notifier
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

def check_video_comments(oid, bv_id, title, header, seen_ids, owner_mid=None):
    """
    检查单个视频的评论
    只监控视频作者(owner_mid)自己的评论
    """
    new_comments_found = []
    
    try:
        latest_comments = fetch_latest_comments(oid, header)
        if not latest_comments:
            return False, []
        
        for comment in latest_comments:
            commenter_mid = str(comment['member']['mid'])
            
            # 只监控视频作者自己的评论
            if owner_mid and commenter_mid != owner_mid:
                # 仍然添加到已见列表，避免重复检查，但不通知
                rpid = comment['rpid_str']
                if rpid not in seen_ids:
                    seen_ids.add(rpid)
                    db.add_comment_to_db(rpid, oid)
                continue
            
            new_main_comment = process_and_notify_comment(comment, oid, seen_ids)
            if new_main_comment:
                new_comments_found.append(new_main_comment)
            
            # 检查子评论（同样只监控作者自己的回复）
            if comment.get('replies'):
                for sub_reply in comment['replies']:
                    sub_commenter_mid = str(sub_reply['member']['mid'])
                    if owner_mid and sub_commenter_mid != owner_mid:
                        # 跳过非作者的子评论，但记录到已见列表
                        sub_rpid = sub_reply['rpid_str']
                        if sub_rpid not in seen_ids:
                            seen_ids.add(sub_rpid)
                            db.add_comment_to_db(sub_rpid, oid)
                        continue
                    
                    new_sub_comment = process_and_notify_comment(sub_reply, oid, seen_ids,
                                                                 parent_user_name=comment['member']['uname'])
                    if new_sub_comment:
                        new_comments_found.append(new_sub_comment)
            
            # 获取更多子评论
            rcount = comment.get('rcount', 0)
            initial_reply_count = len(comment.get('replies') or [])
            
            if rcount > initial_reply_count:
                all_sub_replies = fetch_all_sub_replies(oid, comment['rpid_str'], header)
                for sub_reply in all_sub_replies:
                    sub_commenter_mid = str(sub_reply['member']['mid'])
                    if owner_mid and sub_commenter_mid != owner_mid:
                        # 跳过非作者的子评论，但记录到已见列表
                        sub_rpid = sub_reply['rpid_str']
                        if sub_rpid not in seen_ids:
                            seen_ids.add(sub_rpid)
                            db.add_comment_to_db(sub_rpid, oid)
                        continue
                    
                    new_hidden_comment = process_and_notify_comment(sub_reply, oid, seen_ids,
                                                                    parent_user_name=comment['member']['uname'])
                    if new_hidden_comment:
                        new_comments_found.append(new_hidden_comment)
        
        return len(new_comments_found) > 0, new_comments_found
    except Exception as e:
        log(f"检查视频 {title} 时出错: {e}")
        return False, []

def update_user_latest_video(mid, uname, header):
    """
    获取用户最新的一个视频，并更新到监控列表
    只保留该用户最新的一个视频，移除该用户之前的老视频
    
    Returns:
        (新视频bvid, 新视频标题) 或 (None, None)
    """
    try:
        # 获取用户最新的视频（只取第一个）
        videos_list = user_monitor.get_user_dynamic_videos(mid, header, limit=1)
        if not videos_list:
            return None, None
        
        new_bvid, new_title = videos_list[0]
        
        # 检查这个视频是否已经在监控列表中
        existing_bvids = db.get_dynamic_video_bvids()
        if new_bvid in existing_bvids:
            # 视频已经在监控列表中，不需要更新
            return None, None
        
        # 获取该用户之前监控的视频
        old_videos = db.get_user_dynamic_videos(mid)
        
        # 获取新视频的详细信息
        oid, video_title, owner_mid = get_information(new_bvid, header)
        if not oid or not video_title:
            return None, None
        
        # 移除该用户之前的老视频
        for old_bvid, old_title in old_videos:
            if old_bvid != new_bvid:
                db.remove_video_by_bvid(old_bvid)
                log(f"[移除] 用户 [{uname}] 的老视频: {old_title}")
        
        # 添加新视频到监控列表
        if db.add_video_to_db(oid, new_bvid, video_title, owner_mid):
            db.add_dynamic_video(new_bvid, mid, video_title)
            log(f"[添加] 用户 [{uname}] 的最新视频: {video_title}")
            return new_bvid, video_title
        
        return None, None
    except Exception as e:
        log(f"[错误] 更新用户 {uname} 最新视频时出错: {e}")
        return None, None


def update_user_latest_dynamic(mid, uname, header):
    """
    获取用户最新的动态，并更新到监控列表
    只保留该用户最新的一个动态，移除该用户之前的老动态
    
    Returns:
        (新动态ID, 新动态内容) 或 (None, None)
    """
    try:
        # 获取用户最新的动态（包括图文、文字、视频等）
        log(f"[动态] 正在获取用户 {uname}({mid}) 的最新动态...")
        dynamics = user_monitor.get_user_dynamics(mid, header, limit=5)
        if not dynamics:
            log(f"[动态] 用户 {uname} 没有动态")
            return None, None
        
        # 取最新的一个动态
        latest_dynamic = dynamics[0]
        new_dynamic_id = latest_dynamic['dynamic_id']
        new_content = latest_dynamic['content'][:50] if latest_dynamic['content'] else '[无内容]'
        new_dynamic_type = latest_dynamic['type']
        
        # 检查这个动态是否已经在监控列表中
        existing_dynamic_ids = {d[0] for d in db.get_user_monitored_dynamics(mid)}
        if new_dynamic_id in existing_dynamic_ids:
            # 动态已经在监控列表中，不需要更新
            log(f"[动态] 用户 {uname} 的最新动态已经在监控列表中")
            return None, None
        
        # 获取该用户之前监控的动态
        old_dynamics = db.get_user_monitored_dynamics(mid)
        
        # 移除该用户之前的老动态
        for old_dynamic_id, _, _, _, _, _ in old_dynamics:
            if old_dynamic_id != new_dynamic_id:
                db.remove_monitored_dynamic(old_dynamic_id)
                log(f"[移除] 用户 [{uname}] 的老动态: {old_dynamic_id}")
        
        # 添加新动态到监控列表
        if db.add_monitored_dynamic(new_dynamic_id, mid, latest_dynamic['content'], new_dynamic_type):
            log(f"[添加] 用户 [{uname}] 的最新动态: {new_content}... (类型: {new_dynamic_type})")
            return new_dynamic_id, new_content
        
        return None, None
    except Exception as e:
        log(f"[错误] 更新用户 {uname} 最新动态时出错: {e}")
        return None, None


def check_dynamic_comments(dynamic_id, mid, content, header, seen_ids):
    """
    检查单个动态的评论
    只监控动态作者(发布者)自己的评论
    """
    new_comments_found = []
    
    try:
        # 获取动态的所有评论
        comments = user_monitor.fetch_all_dynamic_comments(dynamic_id, header)
        if not comments:
            return False, []
        
        for comment in comments:
            commenter_mid = str(comment['mid'])
            rpid = comment['rpid']
            
            # 只监控动态作者自己的评论
            if commenter_mid != mid:
                # 仍然添加到已见列表，避免重复检查，但不通知
                if rpid not in seen_ids:
                    seen_ids.add(rpid)
                    db.add_dynamic_comment_to_db(rpid, dynamic_id)
                continue
            
            # 检查是否是新评论
            if rpid not in seen_ids:
                seen_ids.add(rpid)
                db.add_dynamic_comment_to_db(rpid, dynamic_id)
                
                from datetime import datetime
                import pandas as pd
                
                new_comments_found.append({
                    "user": comment['uname'],
                    "message": comment['message'],
                    "time": pd.to_datetime(comment["ctime"], unit='s', utc=True).tz_convert('Asia/Shanghai'),
                    "type": "动态评论"
                })
        
        return len(new_comments_found) > 0, new_comments_found
    except Exception as e:
        log(f"检查动态 {content[:30]}... 时出错: {e}")
        return False, []

def auto_monitor():
    """自动监控所有配置的视频和用户"""
    # 初始化数据库（包括迁移）
    db.init_db()
    
    log("=" * 50)
    log("B站评论自动监控系统启动")
    log("=" * 50)
    
    # 获取请求头
    try:
        header = get_header()
        log("Cookie验证成功")
    except Exception as e:
        log(f"Cookie验证失败: {e}")
        sys.exit(1)
    
    # 获取所有监控的视频
    videos = db.get_monitored_videos()
    if not videos:
        log("数据库中没有视频，尝试从用户动态获取...")
    else:
        log(f"数据库中有 {len(videos)} 个视频")
    
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
    
    # 自动添加/更新用户最新视频（只保留最新一个）
    if dynamic_users:
        log("[动态] 检查并更新用户最新视频...")
        added_count = 0
        
        for mid, uname in dynamic_users.items():
            new_bvid, new_title = update_user_latest_video(mid, uname, header)
            if new_bvid:
                added_count += 1
                time.sleep(0.5)
        
        if added_count > 0:
            log(f"[完成] 更新了 {added_count} 个用户的最新视频")
        else:
            log("[完成] 所有用户的最新视频已在监控列表中")
        
        # 自动添加/更新用户动态（保留所有动态）
        log("[动态] 检查并更新用户动态...")
        dynamic_added_count = 0
        
        for mid, uname in dynamic_users.items():
            new_dynamic_id, new_content = update_user_latest_dynamic(mid, uname, header)
            if new_dynamic_id:
                dynamic_added_count += 1
                time.sleep(0.5)
        
        if dynamic_added_count > 0:
            log(f"[完成] 添加了 {dynamic_added_count} 个用户的新动态")
        else:
            log("[完成] 所有用户的动态已在监控列表中")
    
    # 重新获取视频列表
    videos = db.get_monitored_videos()
    
    if videos:
        log(f"开始监控 {len(videos)} 个视频")
        for v in videos:
            owner_info = f" (作者MID: {v[3]})" if v[3] else ""
            log(f"   - {v[2]} ({v[1]}){owner_info}")
    else:
        log("没有视频可监控，仅监控动态")
    
    # 获取监控间隔
    interval, schedule_name = db.get_current_interval()
    log(f"当前监控频率: {schedule_name} ({interval}秒)")
    
    # 初始化Webhook
    webhook_enabled = notifier.check_webhook_configured()
    if webhook_enabled:
        log("[通知] Webhook通知已启用")
    
    # 初始化视频监控数据
    video_targets = {}
    total_seen = 0
    if videos:
        for oid, bv_id, title, owner_mid in videos:
            video_targets[oid] = {
                "title": title,
                "bv_id": bv_id,
                "owner_mid": owner_mid,
                "seen_ids": db.load_seen_comments_for_video(oid)
            }
            seen_count = len(video_targets[oid]['seen_ids'])
            total_seen += seen_count
    
    log(f"准备就绪！共 {total_seen} 条历史评论")
    log("=" * 50)
    
    # 初始化动态监控数据
    dynamic_targets = {}
    monitored_dynamics = db.get_monitored_dynamics()
    if monitored_dynamics:
        log(f"[动态] 共 {len(monitored_dynamics)} 个动态在监控中")
        for dynamic_id, mid, content, dynamic_type, added_at, uname in monitored_dynamics:
            dynamic_targets[dynamic_id] = {
                "mid": mid,
                "content": content[:50] if content else '[无内容]',
                "uname": uname,
                "seen_ids": db.load_seen_dynamic_comments(dynamic_id)
            }
    
    # 开始监控循环
    loop_count = 0
    try:
        while True:
            loop_count += 1
            log(f"\n第 {loop_count} 轮监控开始")
            
            # 每10轮检查一次用户是否有新视频/动态
            if loop_count % 10 == 0 and dynamic_users:
                log("[动态] 检查用户是否有新视频...")
                for mid, uname in dynamic_users.items():
                    new_bvid, new_title = update_user_latest_video(mid, uname, header)
                    if new_bvid:
                        time.sleep(0.5)
                
                log("[动态] 检查用户是否有新动态...")
                for mid, uname in dynamic_users.items():
                    new_dynamic_id, new_content = update_user_latest_dynamic(mid, uname, header)
                    if new_dynamic_id:
                        time.sleep(0.5)
            
            # 重新获取视频列表（可能有新视频）
            current_videos = db.get_monitored_videos()
            current_oids = {v[0] for v in current_videos}
            
            # 添加新视频到监控，移除已删除的视频
            for oid, bv_id, title, owner_mid in current_videos:
                if oid not in video_targets:
                    video_targets[oid] = {
                        "title": title,
                        "bv_id": bv_id,
                        "owner_mid": owner_mid,
                        "seen_ids": db.load_seen_comments_for_video(oid)
                    }
                    log(f"新视频加入监控: {title}")
            
            # 清理已删除的视频
            oids_to_remove = [oid for oid in video_targets if oid not in current_oids]
            for oid in oids_to_remove:
                del video_targets[oid]
            
            # 重新获取动态列表
            current_dynamics = db.get_monitored_dynamics()
            current_dynamic_ids = {d[0] for d in current_dynamics}
            
            # 添加新动态到监控
            for dynamic_id, mid, content, dynamic_type, added_at, uname in current_dynamics:
                if dynamic_id not in dynamic_targets:
                    dynamic_targets[dynamic_id] = {
                        "mid": mid,
                        "content": content[:50] if content else '[无内容]',
                        "uname": uname,
                        "seen_ids": db.load_seen_dynamic_comments(dynamic_id)
                    }
                    log(f"[动态] 新动态加入监控: {uname} - {content[:30]}...")
            
            # 清理已删除的动态
            dynamic_ids_to_remove = [did for did in dynamic_targets if did not in current_dynamic_ids]
            for did in dynamic_ids_to_remove:
                log(f"[动态] 移除监控的动态: {dynamic_targets[did]['uname']} - {dynamic_targets[did]['content'][:30]}...")
                del dynamic_targets[did]
            
            # 检查视频评论
            round_new = 0
            for oid, data in video_targets.items():
                title = data['title']
                seen_ids = data['seen_ids']
                owner_mid = data.get('owner_mid')
                
                try:
                    has_new, new_comments = check_video_comments(
                        oid, data['bv_id'], title, header, seen_ids, owner_mid
                    )
                    
                    if has_new:
                        log(f"[新评论] [{title}] 发现 {len(new_comments)} 则新评论！")
                        for c in new_comments:
                            log(f"   [{c['type']}] {c['user']}: {c['message'][:50]}...")
                        
                        if webhook_enabled:
                            notifier.send_webhook_notification(title, new_comments)
                    else:
                        log(f"[检查] [{title}] 无新评论")
                    
                    time.sleep(1)  # 避免请求过快
                except Exception as e:
                    log(f"检查视频 {title} 时出错: {e}")
            
            # 检查动态评论
            for dynamic_id, data in dynamic_targets.items():
                mid = data['mid']
                content = data['content']
                uname = data['uname']
                seen_ids = data['seen_ids']
                
                try:
                    has_new, new_comments = check_dynamic_comments(
                        dynamic_id, mid, content, header, seen_ids
                    )
                    
                    if has_new:
                        log(f"[新动态评论] [{uname}] 发现 {len(new_comments)} 则新评论！")
                        for c in new_comments:
                            log(f"   [{c['type']}] {c['user']}: {c['message'][:50]}...")
                        
                        if webhook_enabled:
                            notifier.send_webhook_notification(f"动态: {content[:30]}...", new_comments)
                    else:
                        log(f"[检查] [{uname}] 的动态无新评论")
                    
                    time.sleep(1)  # 避免请求过快
                except Exception as e:
                    log(f"检查动态 {content[:30]}... 时出错: {e}")
            
            # 检查是否需要更新监控间隔
            current_interval, current_schedule = db.get_current_interval()
            if current_interval != interval:
                interval = current_interval
                log(f"监控频率已更新: {current_schedule} ({interval}秒)")
            
            log(f"第 {loop_count} 轮监控完成，{interval}秒后继续...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        log("\n监控已停止")
    except Exception as e:
        log(f"监控出错: {e}")
        raise

if __name__ == "__main__":
    auto_monitor()
