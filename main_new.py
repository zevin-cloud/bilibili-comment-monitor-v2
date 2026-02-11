# filename: main.py (重构版 - 使用新的监控引擎)
import re
import sys
import requests
import json
import time
import datetime
import subprocess
import platform

if platform.system() == "Windows":
    import msvcrt
else:
    import select

import database as db
import notifier
import bvget
from core import MonitorEngine
from api import BilibiliAPI
from models import VideoActivity


def get_header():
    """从 'bili_cookie.txt' 读取 cookie 并构建请求头。"""
    try:
        with open('bili_cookie.txt', 'r', encoding='utf-8') as f:
            cookie = f.read().strip()
        if not cookie:
            raise FileNotFoundError("Cookie 文件为空。")
    except FileNotFoundError:
        print("提示：'bili_cookie.txt' 文件未找到或为空。")
        print("正在尝试调用 'login_bilibili.py' 进行自动登录...")
        try:
            subprocess.run(
                [sys.executable, 'login_bilibili.py'],
                check=False,
                encoding='utf-8'
            )
            print("登录脚本执行完毕，将重新读取 Cookie。")
            with open('bili_cookie.txt', 'r', encoding='utf-8') as f:
                cookie = f.read().strip()
            if not cookie:
                print("错误：登录后 'bili_cookie.txt' 仍然为空，请手动检查登录过程是否成功。")
                sys.exit(1)

            print("\n" + "=" * 15)
            print("检测到新登录，尝试自动获取您投稿的所有视频...")

            temp_header = {
                "Cookie": cookie,
                "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                "Referer": "https://www.bilibili.com"
            }

            all_bvids = bvget.get_all_bvids_from_api()
            if all_bvids:
                print(f"成功获取到 {len(all_bvids)} 个视频，正在添加到监控数据库...")
                added_count = 0
                
                api = BilibiliAPI(temp_header)
                for bv_id in all_bvids:
                    oid, title, owner_mid = api.get_video_info(bv_id)
                    if oid and title:
                        if db.add_video_to_db(oid, bv_id, title, owner_mid):
                            added_count += 1
                    time.sleep(0.5)

                if added_count > 0:
                    print(f"✅ 成功添加 {added_count} 个新视频到数据库。")
                else:
                    print("ℹ️ 所有视频均已存在于数据库中，未添加新视频。")
            else:
                print("⚠️ 未能获取到视频列表，请稍后在菜单中手动添加。")
            print("=" * 15 + "\n")

        except FileNotFoundError:
            print("\n错误：无法在当前目录下找到 'login_bilibili.py'。")
            print("请确保登录脚本与主脚本在同一个文件夹中，或手动创建 'bili_cookie.txt' 文件。")
            sys.exit(1)
        except Exception as e:
            print(f"\n错误：在尝试登录并读取 Cookie 时发生意外错误: {e}")
            sys.exit(1)

    header = {
        "Cookie": cookie,
        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        "Referer": "https://www.bilibili.com"
    }
    return header


def display_user_management_menu(header):
    """顯示用戶監控管理菜單。"""
    while True:
        print("\n" + "=" * 20 + " 用戶監控管理 " + "=" * 20)
        users = db.get_monitored_users()
        
        if not users:
            print("當前沒有監控任何用戶。")
        else:
            print("已監控的用戶列表:")
            for i, (mid, uname, monitor_comments, monitor_dynamic) in enumerate(users):
                comment_status = "✓" if monitor_comments else "✗"
                dynamic_status = "✓" if monitor_dynamic else "✗"
                print(f"  [{i + 1}] {uname} (UID: {mid})")
                print(f"       監控評論: {comment_status} | 監控動態: {dynamic_status}")

        print("\n操作選項:")
        print("  - 輸入 'a' 添加用戶到監控列表。")
        print("  - 輸入 'd' 按用戶名搜索並添加用戶。")
        print("  - 輸入 'r' 移除監控用戶。")
        print("  - 輸入 't' 切換用戶的監控設置。")
        print("  - 輸入 'q' 返回主菜單。")
        
        choice = input("\n請輸入您的選擇: ").strip().lower()
        
        if choice == 'a':
            mid_input = input("請輸入用戶UID (多個請用逗號或空格隔開): ").strip()
            mids = [m.strip() for m in re.split(r'[\s,]+', mid_input) if m.strip()]
            
            api = BilibiliAPI(header)
            for mid in mids:
                uname, _ = api.get_user_info(mid)
                if uname:
                    monitor_comments = input(f"是否監控 [{uname}] 的評論? (y/n, 默認y): ").strip().lower() != 'n'
                    monitor_dynamic = input(f"是否監控 [{uname}] 的動態視頻? (y/n, 默認y): ").strip().lower() != 'n'
                    
                    if db.add_monitored_user(mid, uname, 
                                           1 if monitor_comments else 0, 
                                           1 if monitor_dynamic else 0):
                        print(f"✅ 成功添加 [{uname}] 到監控列表。")
                    else:
                        print(f"❌ 添加 [{uname}] 失敗。")
                else:
                    print(f"❌ 無法獲取用戶 {mid} 的信息，請檢查UID是否正確。")
                time.sleep(0.5)
                
        elif choice == 'd':
            keyword = input("請輸入用戶名關鍵詞進行搜索: ").strip()
            if keyword:
                print(f"正在搜索用戶 '{keyword}'...")
                api = BilibiliAPI(header)
                found_users = api.search_user_by_keyword(keyword)
                if found_users:
                    print(f"找到 {len(found_users)} 個用戶:")
                    for i, (mid, uname) in enumerate(found_users[:10]):
                        print(f"  [{i + 1}] {uname} (UID: {mid})")
                    
                    select = input("請輸入編號選擇用戶 (多個請用逗號隔開，或直接回車取消): ").strip()
                    if select:
                        try:
                            indices = [int(i.strip()) - 1 for i in select.split(',')]
                            for idx in indices:
                                if 0 <= idx < len(found_users):
                                    mid, uname = found_users[idx]
                                    monitor_comments = input(f"是否監控 [{uname}] 的評論? (y/n, 默認y): ").strip().lower() != 'n'
                                    monitor_dynamic = input(f"是否監控 [{uname}] 的動態視頻? (y/n, 默認y): ").strip().lower() != 'n'
                                    
                                    if db.add_monitored_user(mid, uname,
                                                           1 if monitor_comments else 0,
                                                           1 if monitor_dynamic else 0):
                                        print(f"✅ 成功添加 [{uname}] 到監控列表。")
                                    else:
                                        print(f"❌ 添加 [{uname}] 失敗。")
                        except ValueError:
                            print("錯誤：請輸入正確的數字格式。")
                else:
                    print("未找到匹配的用戶。")
                    
        elif choice == 'r':
            if not users:
                print("沒有用戶可以移除。")
                continue
            remove_choice = input("請輸入要移除的用戶編號: ").strip()
            try:
                idx = int(remove_choice) - 1
                if 0 <= idx < len(users):
                    mid_to_remove, uname_to_remove, _, _ = users[idx]
                    confirm = input(f"確定要移除監控用戶 [{uname_to_remove}] 嗎? (y/n): ").lower()
                    if confirm == 'y':
                        if db.remove_monitored_user(mid_to_remove):
                            print(f"✅ 已成功移除 [{uname_to_remove}]。")
                        else:
                            print("❌ 移除失敗。")
                else:
                    print("錯誤：無效的編號。")
            except ValueError:
                print("錯誤：請輸入一個數字。")
                
        elif choice == 't':
            if not users:
                print("沒有用戶可以設置。")
                continue
            toggle_choice = input("請輸入要設置的用戶編號: ").strip()
            try:
                idx = int(toggle_choice) - 1
                if 0 <= idx < len(users):
                    mid, uname, curr_comments, curr_dynamic = users[idx]
                    print(f"當前設置 - 監控評論: {'是' if curr_comments else '否'}, 監控動態: {'是' if curr_dynamic else '否'}")
                    
                    new_comments = input("是否監控該用戶的評論? (y/n): ").strip().lower()
                    new_dynamic = input("是否監控該用戶的動態視頻? (y/n): ").strip().lower()
                    
                    db.update_user_monitor_settings(
                        mid,
                        monitor_comments=1 if new_comments == 'y' else 0 if new_comments == 'n' else None,
                        monitor_dynamic=1 if new_dynamic == 'y' else 0 if new_dynamic == 'n' else None
                    )
                    print(f"✅ 已更新 [{uname}] 的監控設置。")
                else:
                    print("錯誤：無效的編號。")
            except ValueError:
                print("錯誤：請輸入一個數字。")
                
        elif choice == 'q':
            break
        else:
            print("無效的輸入，請重新選擇。")


def display_main_menu():
    """显示主菜单并处理用户交互"""
    header = get_header()
    api = BilibiliAPI(header)
    selected_videos = {}

    while True:
        print("\n" + "=" * 20 + " B站评论监控菜单 " + "=" * 20)
        saved_videos = db.get_monitored_videos()
        if not saved_videos:
            print("数据库中没有已保存的视频。请先添加。")
        else:
            print("已保存的视频列表:")
            for i, (oid, bv_id, title) in enumerate(saved_videos):
                print(f"  [{i + 1}] {title} ({bv_id})")

        print("\n操作选项:")
        print("  - 输入数字 (如 1,3) 选择列表中的视频加入本次监控。")
        print("  - 输入 'a' 添加新的视频 BV 号到数据库。")
        print("  - 输入 'r' 移除数据库中的视频。")
        print("  - 输入 'u' 管理用戶監控設置。")
        print("  - 输入 's' 开始监控已选择的视频。")
        print("  - 输入 'q' 退出程序。")

        if selected_videos:
            print("\n当前已选择:")
            for data in selected_videos.values():
                print(f"  -> 【{data['title']}】")

        choice = input("\n请输入您的选择: ").strip().lower()

        if choice.replace(',', '').replace(' ', '').isdigit():
            try:
                indices = [int(i.strip()) - 1 for i in choice.split(',')]
                for i in indices:
                    if 0 <= i < len(saved_videos):
                        oid, bv_id, title = saved_videos[i]
                        selected_videos[oid] = {"title": title, "bv_id": bv_id}
                        print(f"已选择: 【{title}】")
                    else:
                        print(f"错误：数字 {i + 1} 无效。")
            except ValueError:
                print("错误：请输入正确的数字格式。")

        elif choice == 'a':
            bv_input = input("请输入要添加的新 BV 号 (多个请用逗号或空格隔开): ").strip()
            bvs = [bv.strip() for bv in re.split(r'[\s,]+', bv_input) if bv.strip()]
            for bv in bvs:
                oid, title, owner_mid = api.get_video_info(bv)
                if oid and title:
                    if db.add_video_to_db(oid, bv, title, owner_mid):
                        print(f"成功将【{title}】添加到数据库。")
                time.sleep(1)

        elif choice == 'r':
            if not saved_videos: continue
            remove_choice = input("请输入要移除的视频编号: ").strip()
            try:
                idx = int(remove_choice) - 1
                if 0 <= idx < len(saved_videos):
                    oid_to_remove, _, title_to_remove = saved_videos[idx]
                    confirm = input(f"确定要从数据库移除【{title_to_remove}】吗? (y/n): ").lower()
                    if confirm == 'y':
                        if db.remove_video_from_db(oid_to_remove):
                            print(f"已成功移除【{title_to_remove}】。")
                            if oid_to_remove in selected_videos:
                                del selected_videos[oid_to_remove]
                        else:
                            print("移除失败。")
                else:
                    print("错误：无效的编号。")
            except ValueError:
                print("错误：请输入一个数字。")
        
        elif choice == 'u':
            display_user_management_menu(header)

        elif choice == 's':
            if not selected_videos:
                print("错误：您还没有选择任何要监控的视频。")
            else:
                return list(selected_videos.items())

        elif choice == 'q':
            print("程序退出。")
            sys.exit(0)

        else:
            print("无效的输入，请重新选择。")


if __name__ == "__main__":
    try:
        import requests
        import pandas
    except ImportError as e:
        print(f"缺少必要的库: {e.name}。请使用 'pip install {e.name}' 来安装它。")
        sys.exit(1)

    db.init_db()
    targets = display_main_menu()

    if targets:
        interval_minutes = 5
        try:
            user_input = input(f"\n请输入检查间隔（分钟，直接按 Enter 使用默认值 {interval_minutes} 分钟）: ").strip()
            if user_input:
                interval_minutes = float(user_input)
        except ValueError:
            print(f"输入无效，将使用默认值 {interval_minutes} 分钟。")

        interval_seconds = int(interval_minutes * 60)
        if interval_seconds < 30:
            print("警告：时间间隔过短，已自动设为最低 30 秒，以避免请求过于频繁。")
            interval_seconds = 30

        webhook_enabled = False
        if notifier.check_webhook_configured():
            while True:
                enable_choice = input("\n检测到 Webhook 配置文件，是否启用通知功能? (y/n): ").strip().lower()
                if enable_choice == 'y':
                    webhook_enabled = True
                    print("✅ Webhook 通知已启用。")
                    break
                elif enable_choice == 'n':
                    webhook_enabled = False
                    print("❌ Webhook 通知已禁用。")
                    break
                else:
                    print("输入无效，请输入 'y' 或 'n'。")
        else:
            print("\n提示：未找到有效的 'webhook_config.txt' 文件，Webhook 通知功能将保持禁用。")
            print("如需启用，请创建该文件并在其中填入您的 Webhook URL。")
        
        enable_user_filter = False
        enable_dynamic_monitor = False
        
        monitored_users = db.get_monitored_users()
        if monitored_users:
            print("\n" + "=" * 20 + " 用戶監控功能設置 " + "=" * 20)
            
            comment_users = [u for u in monitored_users if u[2]]
            if comment_users:
                while True:
                    filter_choice = input(f"\n檢測到 {len(comment_users)} 個評論監控用戶，是否只監控這些用戶的評論? (y/n): ").strip().lower()
                    if filter_choice == 'y':
                        enable_user_filter = True
                        print("✅ 用戶評論過濾已啟用，將只監控指定用戶的評論。")
                        break
                    elif filter_choice == 'n':
                        enable_user_filter = False
                        print("❌ 用戶評論過濾已禁用，將監控所有評論。")
                        break
                    else:
                        print("输入无效，请输入 'y' 或 'n'。")
            
            dynamic_users = [u for u in monitored_users if u[3]]
            if dynamic_users:
                while True:
                    dynamic_choice = input(f"\n檢測到 {len(dynamic_users)} 個動態監控用戶，是否自動添加他們的新視頻到監控列表? (y/n): ").strip().lower()
                    if dynamic_choice == 'y':
                        enable_dynamic_monitor = True
                        print("✅ 動態視頻監控已啟用，將自動添加用戶新發布的視頻。")
                        break
                    elif dynamic_choice == 'n':
                        enable_dynamic_monitor = False
                        print("❌ 動態視頻監控已禁用。")
                        break
                    else:
                        print("输入无效，请输入 'y' 或 'n'。")

        header = get_header()
        engine = MonitorEngine(header)
        engine.initialize(
            webhook_enabled=webhook_enabled,
            owner_only=enable_user_filter,
            enable_dynamic_monitor=enable_dynamic_monitor
        )
        
        engine.run_monitoring_loop()
