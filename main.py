# filename: main.py (已更新)
import re
import sys
import requests
import json
import hashlib
import urllib.parse
import time
import datetime
import pandas as pd
import subprocess
import platform  # 导入 platform 模块来判断操作系统

# 根据操作系统导入不同的模块
if platform.system() == "Windows":
    import msvcrt
else:
    import select

# 导入我们自己的模块
import database as db
import notifier
import bvget  # <-- 新增：导入 bvget 模块
import user_monitor  # <-- 新增：导入用户监控模块


# --- 核心功能函数 ---

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

            # vvv 新增：登录成功后，自动获取该账号下的所有视频 vvv
            print("\n" + "=" * 15)
            print("检测到新登录，尝试自动获取您投稿的所有视频...")

            # 为了调用 get_information, 我们需要一个临时的 header
            temp_header_for_bv_fetch = {
                "Cookie": cookie,
                "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                "Referer": "https://www.bilibili.com"
            }

            all_bvids = bvget.get_all_bvids_from_api()
            if all_bvids:
                print(f"成功获取到 {len(all_bvids)} 个视频，正在添加到监控数据库...")
                added_count = 0
                for bv_id in all_bvids:
                    # 使用现有函数获取视频详细信息
                    oid, title = get_information(bv_id, temp_header_for_bv_fetch)
                    if oid and title:
                        # 使用现有函数添加到数据库，它会自动处理重复项
                        if db.add_video_to_db(oid, bv_id, title):
                            added_count += 1
                    time.sleep(0.5)  # 短暂延时，避免API请求过快

                if added_count > 0:
                    print(f"✅ 成功添加 {added_count} 个新视频到数据库。")
                else:
                    print("ℹ️ 所有视频均已存在于数据库中，未添加新视频。")
            else:
                print("⚠️ 未能获取到视频列表，请稍后在菜单中手动添加。")
            print("=" * 15 + "\n")
            # ^^^ 新增 ^^^

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


def get_information(bv, header):
    """通过API获取视频的 'oid' (即 'aid') 和视频标题。"""
    print(f"正在获取视频 {bv} 的信息...")
    api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv}"
    try:
        resp = requests.get(api_url, headers=header, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') == 0:
            video_data = data.get('data', {})
            oid = video_data.get('aid')
            title = video_data.get('title')
            if oid and title:
                print(f"  - [API] 成功获取: 【{title.strip()}】")
                return str(oid), title.strip()
    except Exception as e:
        print(f"  - [警告] API请求失败: {e}。")
    print(f"  - [错误] 无法通过 API 获取视频 {bv} 的信息，请检查 BV 号是否正确或 Cookie 是否有效。")
    return None, None


def md5(code):
    """对输入字符串执行 MD5 哈希。"""
    MD5 = hashlib.md5()
    MD5.update(code.encode('utf-8'))
    return MD5.hexdigest()


def get_wbi_keys(header):
    """动态获取 WBI 签名所需的 img_key 和 sub_key"""
    try:
        resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=header, timeout=5)
        resp.raise_for_status()
        json_content = resp.json()
        img_url = json_content['data']['wbi_img']['img_url']
        sub_url = json_content['data']['wbi_img']['sub_url']
        img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
        return img_key, sub_key
    except Exception as e:
        print(f"动态获取 WBI keys 失败: {e}，将使用备用盐值")
        return None, None

def enc_wbi(params, img_key, sub_key):
    """为请求参数添加 WBI 签名"""
    mixin_key_enc_tab = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]
    raw_key = img_key + sub_key
    mixin_key = "".join([raw_key[i] for i in mixin_key_enc_tab])[:32]
    curr_time = int(time.time())
    params['wts'] = curr_time
    params = dict(sorted(params.items()))
    # 过滤特殊字符
    params = {
        k: "".join([char for char in str(v) if char not in "!'()*"])
        for k, v in params.items()
    }
    query = urllib.parse.urlencode(params)
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = w_rid
    return params

def fetch_latest_comments(oid, header):
    """抓取给定视频 oid 的第一页最新评论 (顶层评论)。"""
    if not oid: return []
    
    # 动态获取 keys
    img_key, sub_key = get_wbi_keys(header)
    
    params = {
        'oid': oid,
        'type': 1,
        'mode': 2,
        'plat': 1,
        'web_location': 1315875
    }
    
    if img_key and sub_key:
        params = enc_wbi(params, img_key, sub_key)
    else:
        # 退回到旧的硬编码方式（备用）
        mixin_key_salt = "ea1db124af3c7062474693fa704f4ff8"
        params['wts'] = int(time.time())
        query_for_w_rid = urllib.parse.urlencode(sorted(params.items()))
        params['w_rid'] = md5(query_for_w_rid + mixin_key_salt)

    url = f"https://api.bilibili.com/x/v2/reply/wbi/main?{urllib.parse.urlencode(params)}"
    try:
        response = requests.get(url, headers=header, timeout=5)
        response.raise_for_status()
        comment_data = response.json()
        return comment_data.get('data', {}).get('replies', []) or []
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"抓取 oid={oid} 的顶层评论时出错：{e}")
    return []


def fetch_all_sub_replies(oid, root_rpid, header):
    """获取指定根评论 (root_rpid) 下的所有分页回复（子评论）。"""
    all_replies = []
    page_number = 1
    while True:
        url = f"https://api.bilibili.com/x/v2/reply/reply?oid={oid}&type=1&root={root_rpid}&pn={page_number}&ps=20"
        try:
            response = requests.get(url, headers=header, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data.get('code') == 0 and data.get('data'):
                replies = data['data'].get('replies', [])
                if not replies: break
                all_replies.extend(replies)
                page_number += 1
                time.sleep(1)
            else:
                print(f"  - [警告] 获取子评论时响应异常: {data.get('message', '未知错误')}")
                break
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"  - [错误] 请求子评论 API (root={root_rpid}) 时失败: {e}")
            break
    return all_replies


# --- 启动菜单与主逻辑 ---

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
            
            for mid in mids:
                uname, _ = user_monitor.get_user_info(mid, header)
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
                found_users = user_monitor.search_user_by_keyword(keyword, header)
                if found_users:
                    print(f"找到 {len(found_users)} 個用戶:")
                    for i, (mid, uname) in enumerate(found_users[:10]):  # 最多顯示10個
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
    """显示主菜单并处理用户交互，返回用户选择要监控的视频列表。"""
    header = get_header()
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
                oid, title = get_information(bv, header)
                if oid and title:
                    if db.add_video_to_db(oid, bv, title):
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


def process_and_notify_comment(reply, oid, seen_ids, parent_user_name=None, filter_user_mids=None):
    """
    处理单条评论，检查是否为新评论，如果是，则存入数据库并返回格式化信息。
    
    Args:
        reply: 评论数据
        oid: 视频ID
        seen_ids: 已见过的评论ID集合
        parent_user_name: 父评论用户名（用于子评论）
        filter_user_mids: 如果指定，只返回这些用户的评论
    """
    rpid = reply['rpid_str']
    member_mid = str(reply['member']['mid'])
    
    # 如果指定了用户过滤，且当前评论不是指定用户的，则跳过
    if filter_user_mids and member_mid not in filter_user_mids:
        # 仍然添加到已见列表，避免重复检查
        if rpid not in seen_ids:
            seen_ids.add(rpid)
            db.add_comment_to_db(rpid, oid)
        return None
    
    if rpid not in seen_ids:
        seen_ids.add(rpid)
        db.add_comment_to_db(rpid, oid)

        # 判断回复类型
        if parent_user_name:
            # B站API中，对子评论的回复会包含 at_details
            if reply.get('at_details'):
                # 遍历at列表，找到被@的人的用户名
                at_user_name = next(
                    (item['uname'] for item in reply['at_details'] if item['mid'] == reply['parent_str']),
                    parent_user_name)
                comment_type = f"回复@{at_user_name}"
            else:
                comment_type = f"回复@{parent_user_name}"
        else:
            # 主评论
            comment_type = "主评论"

        return {
            "user": reply['member']['uname'],
            "message": reply['content']['message'],
            "time": pd.to_datetime(reply["ctime"], unit='s', utc=True).tz_convert('Asia/Shanghai'),
            "type": comment_type
        }
    return None


def wait_with_manual_trigger(interval_seconds):
    """
    等待指定的秒数，同时监听用户的 Enter 键以立即触发。
    此版本兼容 Windows 和类 Unix 系统。
    """
    minutes = interval_seconds // 60
    seconds = interval_seconds % 60
    wait_message = f"等待 {minutes} 分钟 {seconds} 秒后" if minutes > 0 else f"等待 {seconds} 秒后"

    print(f"\n所有视频检查完毕。{wait_message}进行下一轮检查...")
    print("您可以随时按下 [Enter] 键来立即开始下一轮检查。")

    start_time = time.time()
    while time.time() - start_time < interval_seconds:
        # 根据操作系统使用不同的方法检测输入
        if platform.system() == "Windows":
            # msvcrt.kbhit() 是非阻塞的，它会立即返回是否有按键事件
            if msvcrt.kbhit():
                # msvcrt.getch() 会读取按键，我们检查它是否是 Enter (回车符)
                if msvcrt.getch() in [b'\r', b'\n']:
                    print("\n收到手动触发指令，立即开始新一轮检查！")
                    return  # 立即退出等待
        else:  # Linux, macOS, etc.
            # 使用 select，它在这里工作得很好
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)  # 短暂等待0.1秒
            if readable:
                sys.stdin.readline()  # 清空输入缓冲区
                print("\n收到手动触发指令，立即开始新一轮检查！")
                return  # 立即退出等待

        time.sleep(0.1)  # 短暂休眠，避免 CPU 占用过高


def check_and_add_dynamic_videos(header, verbose=True):
    """
    檢查所有設置了動態監控的用戶，獲取他們的新視頻並添加到監控列表。
    
    Args:
        header: 請求頭
        verbose: 是否顯示詳細日誌
        
    Returns:
        新添加的視頻數量
    """
    dynamic_users = db.get_dynamic_monitored_user_mids()
    if not dynamic_users:
        if verbose:
            print("\n  -> [動態監控] 沒有設置動態監控的用戶")
        return 0
    
    if verbose:
        print(f"\n  -> [動態監控] 正在檢查 {len(dynamic_users)} 個用戶的最新動態...")
        print(f"     用戶列表: {', '.join(dynamic_users.values())}")
    
    new_videos_count = 0
    total_checked = 0
    existing_bvids = db.get_dynamic_video_bvids()
    
    if verbose:
        print(f"     已有 {len(existing_bvids)} 個視頻在監控列表中")
    
    for mid, uname in dynamic_users.items():
        try:
            videos = user_monitor.get_user_dynamic_videos(mid, header, limit=5)
            total_checked += len(videos)
            if verbose and videos:
                print(f"     [{uname}] 獲取到 {len(videos)} 個視頻")
            
            for bvid, title in videos:
                if bvid not in existing_bvids:
                    # 獲取視頻詳細信息
                    oid, video_title = get_information(bvid, header)
                    if oid and video_title:
                        # 添加到視頻監控列表
                        if db.add_video_to_db(oid, bvid, video_title):
                            # 記錄到動態視頻表
                            db.add_dynamic_video(bvid, mid, video_title)
                            if verbose:
                                print(f"     ✚ 從 [{uname}] 的動態添加新視頻: 【{video_title}】")
                            new_videos_count += 1
                        time.sleep(0.5)
                    elif verbose:
                        print(f"     ✗ 無法獲取視頻 {bvid} 的詳細信息")
                elif verbose:
                    print(f"     • 視頻 [{title}] 已在監控列表中，跳過")
        except Exception as e:
            if verbose:
                print(f"     ✗ 檢查用戶 [{uname}] 動態時出錯: {e}")
    
    if verbose:
        if new_videos_count > 0:
            print(f"  -> [動態監控] 共檢查 {total_checked} 個視頻，新增 {new_videos_count} 個到監控列表")
        else:
            print(f"  -> [動態監控] 共檢查 {total_checked} 個視頻，暫無新視頻")
    
    return new_videos_count


def start_monitoring(targets_to_monitor, header, interval, webhook_enabled, enable_user_filter=False, enable_dynamic_monitor=False):
    """
    监控选定视频的新评论，包含获取所有子评论的功能。
    
    Args:
        targets_to_monitor: 要监控的视频列表
        header: 请求头
        interval: 检查间隔（秒）
        webhook_enabled: 是否启用Webhook通知
        enable_user_filter: 是否只监控指定用户的评论
        enable_dynamic_monitor: 是否监控用户动态视频
    """
    video_targets = {}
    
    # 如果用戶過濾啟用，獲取要監控的用戶ID集合
    filter_user_mids = None
    if enable_user_filter:
        filter_user_mids = db.get_comment_monitored_user_mids()
        if filter_user_mids:
            # 獲取用戶名列表用於顯示
            all_users = db.get_monitored_users()
            filtered_names = [u[1] for u in all_users if u[0] in filter_user_mids]
            print(f"\n🎯 用戶過濾已啟用，只監控以下 {len(filter_user_mids)} 個用戶的評論:")
            for name in filtered_names:
                print(f"     - {name}")
        else:
            print("\n⚠️ 用戶過濾已啟用，但沒有設置監控用戶，將監控所有評論")

    print("\n" + "=" * 20 + " 初始化监控数据 " + "=" * 20)
    total_seen = 0
    for oid, data in targets_to_monitor:
        print(f"正在为【{data['title']}】加载历史评论记录...")
        video_targets[oid] = {
            "title": data['title'],
            "seen_ids": db.load_seen_comments_for_video(oid)
        }
        seen_count = len(video_targets[oid]['seen_ids'])
        total_seen += seen_count
        print(f"-> 加载完成，已记录 {seen_count} 则历史评论。")

    print(f"\n✅ 准备就绪！开始监控 {len(video_targets)} 个视频，共 {total_seen} 条历史评论。")
    print("=" * 55)
    
    # 統計信息
    check_count = 0
    total_new_comments = 0

    while True:
        try:
            check_count += 1
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[{now}] 第 {check_count} 轮检查开始...")
            
            # 如果啟用了動態監控，先檢查用戶新視頻
            if enable_dynamic_monitor:
                new_videos = check_and_add_dynamic_videos(header)
                if new_videos > 0:
                    # 重新加載視頻列表
                    print("  -> [動態監控] 重新加載視頻列表...")
                    new_added = 0
                    for oid, bv_id, title in db.get_monitored_videos():
                        if oid not in video_targets:
                            video_targets[oid] = {
                                "title": title,
                                "seen_ids": db.load_seen_comments_for_video(oid)
                            }
                            print(f"     ✚ 已將新視頻【{title}】加入監控")
                            new_added += 1
                    print(f"  -> [動態監控] 本次共新增 {new_added} 個視頻到監控列表")

            round_new_comments = 0
            for oid, data in video_targets.items():
                title = data['title']
                seen_ids = data['seen_ids']
                print(f"  -> [評論監控] 正在检查【{title}】...")

                latest_comments = fetch_latest_comments(oid, header)
                if not latest_comments:
                    print(f"     ⚠️ 未能獲取到評論數據，可能API請求失敗")
                    continue
                    
                print(f"     獲取到 {len(latest_comments)} 條頂層評論")
                new_comments_found = []
                checked_replies = 0

                for comment in latest_comments:
                    commenter_name = comment['member']['uname']
                    commenter_mid = str(comment['member']['mid'])
                    
                    # 檢查是否被過濾
                    if filter_user_mids and commenter_mid not in filter_user_mids:
                        # 靜默跳過，不打擾日誌
                        pass
                    else:
                        new_main_comment = process_and_notify_comment(comment, oid, seen_ids, 
                                                                       filter_user_mids=filter_user_mids)
                        if new_main_comment:
                            new_comments_found.append(new_main_comment)
                            round_new_comments += 1

                    if comment.get('replies'):
                        replies = comment['replies']
                        checked_replies += len(replies)
                        for sub_reply in replies:
                            new_sub_comment = process_and_notify_comment(sub_reply, oid, seen_ids,
                                                                         parent_user_name=comment['member']['uname'],
                                                                         filter_user_mids=filter_user_mids)
                            if new_sub_comment:
                                new_comments_found.append(new_sub_comment)
                                round_new_comments += 1

                    rcount = comment.get('rcount', 0)
                    initial_reply_count = len(comment.get('replies') or [])

                    if rcount > initial_reply_count:
                        print(f"     └─ 發現【{comment['member']['uname']}】的評論有 {rcount} 條回復（已顯示 {initial_reply_count} 條），正在抓取剩餘 {rcount - initial_reply_count} 條...")
                        all_sub_replies = fetch_all_sub_replies(oid, comment['rpid_str'], header)
                        print(f"        成功抓取 {len(all_sub_replies)} 條回復")

                        for sub_reply in all_sub_replies:
                            new_hidden_comment = process_and_notify_comment(sub_reply, oid, seen_ids,
                                                                            parent_user_name=comment['member']['uname'],
                                                                            filter_user_mids=filter_user_mids)
                            if new_hidden_comment:
                                new_comments_found.append(new_hidden_comment)
                                round_new_comments += 1
                
                if checked_replies > 0:
                    print(f"     檢查了 {checked_replies} 條子評論")

                if new_comments_found:
                    total_new_comments += len(new_comments_found)
                    # 对新评论按时间排序
                    sorted_comments = sorted(new_comments_found, key=lambda x: x['time'])

                    # 控制台打印
                    print("*" * 25)
                    print(f"🔥【{title}】发现 {len(sorted_comments)} 则新评论！")
                    print("*" * 25)
                    for new_comment in sorted_comments:
                        print(f"  类型: {new_comment['type']}")
                        print(f"  用户: {new_comment['user']}")
                        print(f"  评论: {new_comment['message']}")
                        print(f"  时间: {new_comment['time'].strftime('%Y-%m-%d %H:%M:%S')}")
                        print("-" * 25)

                    # 如果启用了 Webhook，则发送通知
                    if webhook_enabled:
                        notifier.send_webhook_notification(title, sorted_comments)
                else:
                    print(f"     ✓ 暫無新評論")

                time.sleep(3)  # 检查完一个视频后短暂休息，防止请求过快
            
            # 每輪檢查結束後顯示統計
            print(f"\n📊 第 {check_count} 輪檢查完成統計:")
            print(f"   - 監控視頻數: {len(video_targets)}")
            print(f"   - 本輪新評論: {round_new_comments}")
            print(f"   - 總新評論數: {total_new_comments}")
            if enable_dynamic_monitor:
                dynamic_count = len(db.get_dynamic_video_bvids())
                print(f"   - 動態視頻數: {dynamic_count}")
            
            # 獲取當前時間段應該的監控間隔
            current_interval, schedule_name = db.get_current_interval()
            print(f"   - 當前時間段: {schedule_name} ({current_interval}秒)")

            wait_with_manual_trigger(current_interval)

        except KeyboardInterrupt:
            print("\n程序被用户手动中断 (Ctrl+C)。再见！")
            break
        except Exception as e:
            # 增加错误类型的打印，方便调试
            print(f"\n[严重错误] 监控循环中发生未知错误 ({type(e).__name__}): {e}")
            print("等待 60 秒后重试...")
            time.sleep(60)


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
        # 获取监控间隔
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

        # vvv 新增：Webhook 开关逻辑 vvv
        webhook_enabled = False
        # 检查配置文件是否存在且有效
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
        # ^^^ 新增 ^^^
        
        # vvv 新增：用戶監控功能開關 vvv
        enable_user_filter = False
        enable_dynamic_monitor = False
        
        monitored_users = db.get_monitored_users()
        if monitored_users:
            print("\n" + "=" * 20 + " 用戶監控功能設置 " + "=" * 20)
            
            # 檢查是否有設置評論監控的用戶
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
            
            # 檢查是否有設置動態監控的用戶
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
        # ^^^ 新增 ^^^

        header = get_header()
        # 修改：传入 webhook_enabled 参数
        start_monitoring(targets, header, interval_seconds, webhook_enabled, 
                        enable_user_filter, enable_dynamic_monitor)

