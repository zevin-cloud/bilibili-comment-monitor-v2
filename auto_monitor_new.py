# filename: auto_monitor.py (重构版 - 使用新的监控引擎)
"""自动监控脚本 - 无需交互，直接开始监控"""
import sys
import time
import datetime
from main import get_header
import database as db
import notifier
from core import MonitorEngine


def log(message):
    """打印并记录日志"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = message.encode('gbk', errors='ignore').decode('gbk')
    log_line = f"{timestamp} - {message}"
    print(log_line)
    with open('bilibili_monitor.log', 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')


def auto_monitor():
    """自动监控所有配置的活动"""
    db.init_db()
    
    log("=" * 50)
    log("B站评论自动监控系统启动 (新架构)")
    log("=" * 50)
    
    header = get_header()
    log("Cookie验证成功")
    
    users = db.get_monitored_users()
    if users:
        log(f"[用户] 共 {len(users)} 个监控用户")
        for mid, uname, monitor_comments, monitor_dynamic in users:
            log(f"[用户] {mid} -> {uname} (评论:{'是' if monitor_comments else '否'}, 动态:{'是' if monitor_dynamic else '否'})")
    else:
        log("[用户] 没有监控用户")
    
    webhook_enabled = notifier.check_webhook_configured()
    if webhook_enabled:
        log("[通知] Webhook通知已启用")
    else:
        log("[通知] Webhook通知未启用")
    
    interval, schedule_name = db.get_current_interval()
    log(f"[调度] 当前监控频率: {schedule_name} ({interval}秒)")
    
    engine = MonitorEngine(header)
    engine.initialize(
        webhook_enabled=webhook_enabled,
        owner_only=True,
        enable_dynamic_monitor=True
    )
    
    log("=" * 50)
    log("监控引擎已启动，开始监控...")
    log("=" * 50)
    
    engine.run_monitoring_loop()


if __name__ == "__main__":
    try:
        auto_monitor()
    except KeyboardInterrupt:
        log("\n监控已停止")
    except Exception as e:
        log(f"监控出错: {e}")
        raise
