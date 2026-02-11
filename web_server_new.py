# filename: web_server.py (重构版 - 适配新架构)
from flask import Flask, render_template, jsonify, request
import database as db
import json
import os
import subprocess
import sys
import threading
import time
import requests
from api import BilibiliAPI
from core import MonitorEngine, UserManager, ActivityManager, CommentFilter

app = Flask(__name__, static_folder='templates/static', static_url_path='/static')

monitor_process = None
monitor_thread = None
log_file = 'bilibili_monitor.log'
pid_file = 'monitor.pid'


def write_log(message):
    """写入日志到文件"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f'{timestamp} - {message}\n')


def read_logs():
    """读取日志文件"""
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return f.readlines()
        except:
            return []
    return []


@app.route('/')
def index():
    """主页面"""
    response = render_template('index_new.html')
    return response, 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }


@app.route('/api/videos', methods=['GET'])
def get_videos():
    """获取所有视频"""
    videos = db.get_monitored_videos()
    return jsonify([{
        'oid': v[0],
        'bv_id': v[1],
        'title': v[2],
        'owner_mid': v[3] if len(v) > 3 else None
    } for v in videos])


@app.route('/api/videos', methods=['POST'])
def add_video():
    """添加视频"""
    data = request.json
    bv_id = data.get('bv_id')
    
    if not bv_id:
        return jsonify({'success': False, 'error': 'BV号不能为空'})
    
    try:
        header = {
            'Cookie': open('bili_cookie.txt', 'r', encoding='utf-8').read().strip(),
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': "https://www.bilibili.com"
        }
        
        api = BilibiliAPI(header)
        oid, title, owner_mid = api.get_video_info(bv_id)
        
        if oid and title:
            success = db.add_video_to_db(oid, bv_id, title, owner_mid)
            if success:
                return jsonify({'success': True, 'message': f'成功添加视频: {title}'})
            else:
                return jsonify({'success': False, 'error': '视频已存在'})
        else:
            return jsonify({'success': False, 'error': '无法获取视频信息，请检查BV号是否正确'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'添加视频失败: {str(e)}'})


@app.route('/api/videos/<oid>', methods=['DELETE'])
def delete_video(oid):
    """删除视频"""
    success = db.remove_video_from_db(oid)
    return jsonify({'success': success})


@app.route('/api/users', methods=['GET'])
def get_users():
    """获取所有监控用户"""
    users = db.get_monitored_users()
    return jsonify([{
        'mid': u[0],
        'uname': u[1],
        'monitor_comments': bool(u[2]),
        'monitor_dynamic': bool(u[3])
    } for u in users])


@app.route('/api/users/search', methods=['GET'])
def search_user():
    """通过用户名搜索用户"""
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify({'success': False, 'error': '搜索关键词不能为空'})
    
    try:
        header = {
            'Cookie': open('bili_cookie.txt', 'r', encoding='utf-8').read().strip(),
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://search.bilibili.com'
        }
        
        api = BilibiliAPI(header)
        users = api.search_user_by_keyword(keyword)
        
        return jsonify({
            'success': True,
            'users': [{'mid': mid, 'uname': uname} for mid, uname in users[:10]]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/users', methods=['POST'])
def add_user():
    """添加监控用户，并自动获取最新视频和动态"""
    data = request.json
    mid = data.get('mid')
    uname = data.get('uname', '')
    monitor_comments = data.get('monitor_comments', True)
    monitor_dynamic = data.get('monitor_dynamic', True)

    if not mid:
        return jsonify({'success': False, 'error': '用户ID不能为空'})

    if not uname:
        try:
            header = {
                'Cookie': open('bili_cookie.txt', 'r', encoding='utf-8').read().strip(),
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://space.bilibili.com'
            }
            api = BilibiliAPI(header)
            uname, _ = api.get_user_info(mid)
        except:
            uname = ''

    success = db.add_monitored_user(mid, uname,
                                   1 if monitor_comments else 0,
                                   1 if monitor_dynamic else 0)

    added_items = []

    if success and monitor_dynamic:
        try:
            header = {
                'Cookie': open('bili_cookie.txt', 'r', encoding='utf-8').read().strip(),
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://space.bilibili.com'
            }
            api = BilibiliAPI(header)

            videos = api.get_user_dynamic_videos(mid, limit=1)
            if videos:
                bvid, title = videos[0]
                oid, video_title, owner_mid = api.get_video_info(bvid)
                if oid and video_title:
                    if db.add_video_to_db(oid, bvid, video_title, owner_mid):
                        db.add_dynamic_video(bvid, mid, video_title)
                        added_items.append(f'视频: {video_title}')

            dynamics = api.get_user_dynamics(mid, limit=5)
            valid_dynamics = [d for d in dynamics if d['type'] in [2, 4]]
            if valid_dynamics:
                latest = valid_dynamics[0]
                if db.add_monitored_dynamic(latest['dynamic_id'], mid, latest['content'], latest['type']):
                    content_preview = latest['content'][:30] if latest['content'] else '无内容'
                    added_items.append(f'动态: {content_preview}...')

        except Exception as e:
            print(f"自动获取视频/动态时出错: {e}")

    message = '添加成功'
    if uname:
        message += f': {uname}'
    if added_items:
        message += f' (自动添加: {", ".join(added_items)})'
    else:
        message += ' (用户已添加，未发现新内容)'

    return jsonify({'success': success, 'uname': uname, 'message': message})


@app.route('/api/users/<mid>', methods=['DELETE'])
def delete_user(mid):
    """删除用户"""
    success = db.remove_monitored_user(mid)
    return jsonify({'success': success})


@app.route('/api/activities', methods=['GET'])
def get_activities():
    """获取所有监控的活动（新架构）"""
    try:
        import sqlite3
        with sqlite3.connect(db.DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, activity_type, owner_mid, owner_name, content, title, added_at
                FROM activities 
                WHERE status = 'active'
                ORDER BY added_at DESC
            ''')
            activities = [{
                'id': row[0],
                'activity_type': row[1],
                'owner_mid': row[2],
                'owner_name': row[3],
                'content': row[4],
                'title': row[5],
                'added_at': row[6]
            } for row in cursor.fetchall()]
            return jsonify(activities)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/activities/<activity_id>', methods=['DELETE'])
def delete_activity(activity_id):
    """删除活动监控（新架构）"""
    try:
        import sqlite3
        with sqlite3.connect(db.DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM activity_comments WHERE activity_id = ?', (activity_id,))
            cursor.execute('DELETE FROM activities WHERE id = ?', (activity_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def is_process_running(pid):
    """检查进程是否运行"""
    try:
        subprocess.check_output(['tasklist', '/FI', f'PID eq {pid}'], stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError:
        return False


@app.route('/api/monitor/status', methods=['GET'])
def get_monitor_status():
    """获取监控状态"""
    global monitor_process
    
    is_running = monitor_process is not None and monitor_process.poll() is None
    pid = monitor_process.pid if is_running else None
    
    if not is_running and os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                saved_pid = int(f.read().strip())
            if is_process_running(saved_pid):
                is_running = True
                pid = saved_pid
        except Exception as e:
            print(f"读取PID文件错误: {e}")
    
    return jsonify({
        'running': is_running,
        'pid': pid
    })


def monitor_output_reader():
    """读取监控进程输出并写入日志"""
    global monitor_process
    if not monitor_process:
        return
    
    time.sleep(0.5)
    
    while monitor_process and monitor_process.poll() is None:
        try:
            line = monitor_process.stdout.readline()
            if line:
                write_log(line.strip())
        except Exception as e:
            print(f"日志读取错误: {e}")
            break


@app.route('/api/monitor/start', methods=['POST'])
def start_monitor():
    """开始监控"""
    global monitor_process, monitor_thread
    
    if monitor_process and monitor_process.poll() is None:
        return jsonify({'success': False, 'error': '监控已在运行'})
    
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                saved_pid = int(f.read().strip())
            if is_process_running(saved_pid):
                return jsonify({'success': False, 'error': '监控已在运行'})
        except Exception as e:
            print(f"检查PID文件错误: {e}")
    
    try:
        if os.path.exists(log_file):
            os.remove(log_file)
        
        monitor_process = subprocess.Popen(
            [sys.executable, 'auto_monitor_new.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        with open(pid_file, 'w') as f:
            f.write(str(monitor_process.pid))
        
        monitor_thread = threading.Thread(target=monitor_output_reader, daemon=True)
        monitor_thread.start()
        
        write_log(f'监控进程已启动，PID: {monitor_process.pid}')
        return jsonify({'success': True, 'pid': monitor_process.pid})
    except Exception as e:
        write_log(f'启动监控失败: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/monitor/stop', methods=['POST'])
def stop_monitor():
    """停止监控"""
    global monitor_process
    
    if monitor_process:
        try:
            monitor_process.terminate()
            monitor_process.wait(timeout=5)
            monitor_process = None
            if os.path.exists(pid_file):
                os.remove(pid_file)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                saved_pid = int(f.read().strip())
            if is_process_running(saved_pid):
                subprocess.run(['taskkill', '/PID', str(saved_pid), '/F'], check=True)
            if os.path.exists(pid_file):
                os.remove(pid_file)
            return jsonify({'success': True})
        except Exception as e:
            print(f"停止PID文件中的进程错误: {e}")
            if os.path.exists(pid_file):
                os.remove(pid_file)
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': '监控未在运行'})


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    lines = read_logs()
    if lines:
        return jsonify({'logs': lines[-100:]})
    return jsonify({'logs': []})


@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    """获取所有时间段配置"""
    schedules = db.get_monitor_schedules()
    return jsonify([{
        'id': s[0],
        'name': s[1],
        'start_time': s[2],
        'end_time': s[3],
        'days_of_week': s[4],
        'interval_seconds': s[5],
        'is_active': bool(s[6])
    } for s in schedules])


@app.route('/api/schedules', methods=['POST'])
def add_schedule():
    """添加时间段配置"""
    data = request.json
    name = data.get('name')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    days_of_week = data.get('days_of_week')
    interval_seconds = data.get('interval_seconds')
    
    if not all([name, start_time, end_time, days_of_week, interval_seconds]):
        return jsonify({'success': False, 'error': '所有字段都不能为空'})
    
    success = db.add_monitor_schedule(name, start_time, end_time, days_of_week, interval_seconds)
    return jsonify({'success': success})


@app.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """更新时间段配置"""
    data = request.json
    success = db.update_monitor_schedule(schedule_id, **data)
    return jsonify({'success': success})


@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """删除时间段配置"""
    success = db.delete_monitor_schedule(schedule_id)
    return jsonify({'success': success})


@app.route('/api/current-interval', methods=['GET'])
def get_current_interval():
    """获取当前时间段的监控间隔"""
    interval, name = db.get_current_interval()
    return jsonify({
        'interval_seconds': interval,
        'schedule_name': name
    })


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """获取所有系统设置"""
    settings = db.get_all_settings()
    return jsonify(settings)


@app.route('/api/settings/<key>', methods=['GET'])
def get_setting(key):
    """获取指定设置"""
    value = db.get_system_setting(key)
    return jsonify({'key': key, 'value': value})


@app.route('/api/settings/<key>', methods=['PUT'])
def update_setting(key):
    """更新设置"""
    data = request.json
    value = data.get('value')
    success = db.set_system_setting(key, value)
    return jsonify({'success': success})


@app.route('/api/cookie-status', methods=['GET'])
def get_cookie_status():
    """获取Cookie状态"""
    try:
        import cookie_checker
        header = {
            'Cookie': open('bili_cookie.txt', 'r', encoding='utf-8').read().strip(),
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.bilibili.com'
        }
        result = cookie_checker.get_cookie_expiry_info(header)
        
        expiry_info = None
        try:
            with open('bili_cookie.txt', 'r') as f:
                cookie = f.read().strip()
                if cookie.startswith('SESSDATA='):
                    sessdata = cookie[9:]
                    expiry_info = cookie_checker.parse_sessdata_expiry(sessdata)
        except:
            pass
        
        return jsonify({
            'valid': result.get('valid', False),
            'message': result.get('message', ''),
            'user_info': result.get('user_info', {}),
            'expiry_info': expiry_info
        })
    except Exception as e:
        return jsonify({
            'valid': False,
            'message': f'检查失败: {str(e)}',
            'user_info': {},
            'expiry_info': None
        })


@app.route('/api/update-cookie', methods=['POST'])
def update_cookie():
    """更新Cookie"""
    try:
        data = request.json
        cookie = data.get('cookie', '').strip()
        
        if not cookie:
            return jsonify({'success': False, 'error': 'Cookie不能为空'})
        
        if not cookie.startswith('SESSDATA='):
            cookie = 'SESSDATA=' + cookie
        
        with open('bili_cookie.txt', 'w', encoding='utf-8') as f:
            f.write(cookie)
        
        import cookie_checker
        header = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.bilibili.com'
        }
        result = cookie_checker.get_cookie_expiry_info(header)
        
        if result.get('valid'):
            return jsonify({
                'success': True,
                'message': 'Cookie更新成功',
                'user_info': result.get('user_info', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Cookie无效，请检查',
                'message': result.get('message', '')
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


login_manager = None


@app.route('/api/login/qrcode', methods=['POST'])
def generate_login_qrcode():
    """生成登录二维码"""
    global login_manager
    try:
        from auto_login import AutoLoginManager
        login_manager = AutoLoginManager()
        result = login_manager.generate_qrcode()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/login/poll', methods=['POST'])
def poll_login_status():
    """轮询登录状态"""
    global login_manager
    try:
        if not login_manager:
            return jsonify({'success': False, 'error': '未生成二维码'})
        
        result = login_manager.poll_login_status()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/login/cancel', methods=['POST'])
def cancel_login():
    """取消登录"""
    global login_manager
    try:
        if login_manager:
            login_manager.stop_login()
        return jsonify({'success': True, 'message': '已取消登录'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    db.init_db()
    print("启动Web服务器...")
    print("访问地址: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
