# filename: web_server.py
from flask import Flask, render_template, jsonify, request
import database as db
import json
import os
import subprocess
import sys
import threading
import time
import requests

# 导入用户监控模块
import user_monitor

app = Flask(__name__)

# 监控进程
monitor_process = None
monitor_thread = None
log_file = 'bilibili_monitor.log'

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
    response = render_template('index.html')
    # 禁用缓存
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
        'title': v[2]
    } for v in videos])

@app.route('/api/videos', methods=['POST'])
def add_video():
    """添加视频"""
    data = request.json
    bv_id = data.get('bv_id')
    
    if not bv_id:
        return jsonify({'success': False, 'error': 'BV号不能为空'})
    
    try:
        # 导入main模块获取视频信息
        import main as main_module
        header = main_module.get_header()
        
        # 获取视频信息
        oid, title = main_module.get_information(bv_id, header)
        
        if oid and title:
            # 添加到数据库
            success = db.add_video_to_db(oid, bv_id, title)
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
        # 创建请求头
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://search.bilibili.com'
        }
        
        # 调用搜索函数
        users = user_monitor.search_user_by_keyword(keyword, header)
        
        return jsonify({
            'success': True,
            'users': [{'mid': mid, 'uname': uname} for mid, uname in users[:10]]  # 最多返回10个
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users', methods=['POST'])
def add_user():
    """添加监控用户"""
    data = request.json
    mid = data.get('mid')
    uname = data.get('uname', '')
    monitor_comments = data.get('monitor_comments', True)
    monitor_dynamic = data.get('monitor_dynamic', True)
    
    if not mid:
        return jsonify({'success': False, 'error': '用户ID不能为空'})
    
    # 如果没有提供用户名，尝试获取
    if not uname:
        try:
            header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://space.bilibili.com'
            }
            uname, _ = user_monitor.get_user_info(mid, header)
        except:
            uname = ''
    
    success = db.add_monitored_user(mid, uname, 
                                   1 if monitor_comments else 0,
                                   1 if monitor_dynamic else 0)
    return jsonify({'success': success, 'uname': uname})

@app.route('/api/users/<mid>', methods=['DELETE'])
def delete_user(mid):
    """删除用户"""
    success = db.remove_monitored_user(mid)
    return jsonify({'success': success})

@app.route('/api/monitor/status', methods=['GET'])
def get_monitor_status():
    """获取监控状态"""
    global monitor_process
    is_running = monitor_process is not None and monitor_process.poll() is None
    return jsonify({
        'running': is_running,
        'pid': monitor_process.pid if is_running else None
    })

def monitor_output_reader():
    """读取监控进程输出并写入日志"""
    global monitor_process
    if not monitor_process:
        return
    
    # 等待进程启动
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
    
    try:
        # 清空旧日志
        if os.path.exists(log_file):
            os.remove(log_file)
        
        # 启动监控进程（使用自动监控脚本）
        monitor_process = subprocess.Popen(
            [sys.executable, 'auto_monitor.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # 启动日志读取线程
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
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': '监控未在运行'})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    lines = read_logs()
    if lines:
        # 返回最近100行
        return jsonify({'logs': lines[-100:]})
    return jsonify({'logs': []})


# --- 时间段配置API ---

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


# --- 系统设置API ---

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


# --- 动态视频检查API ---

@app.route('/api/check-dynamic-videos', methods=['POST'])
def check_dynamic_videos():
    """检查用户动态视频并自动添加到监控列表"""
    try:
        # 检查是否开启了自动添加功能
        auto_add = db.get_system_setting('auto_add_user_videos', '1') == '1'
        if not auto_add:
            return jsonify({'success': True, 'message': '自动添加功能已关闭', 'added': []})
        
        # 获取设置了动态监控的用户
        dynamic_users = db.get_dynamic_monitored_user_mids()
        if not dynamic_users:
            return jsonify({'success': True, 'message': '没有设置动态监控的用户', 'added': []})
        
        added_videos = []
        existing_bvids = db.get_dynamic_video_bvids()
        
        # 这里需要获取header，简化处理
        # 实际使用时需要从cookie文件读取
        
        for mid, uname in dynamic_users.items():
            try:
                # 获取用户视频列表
                import user_monitor
                # 创建一个简单的header
                header = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://space.bilibili.com'
                }
                videos = user_monitor.get_user_dynamic_videos(mid, header, limit=5)
                
                for bvid, title in videos:
                    if bvid not in existing_bvids:
                        # 获取视频详细信息
                        import main
                        oid, video_title = main.get_information(bvid, header)
                        if oid and video_title:
                            # 添加到视频监控列表
                            if db.add_video_to_db(oid, bvid, video_title):
                                # 记录到动态视频表
                                db.add_dynamic_video(bvid, mid, video_title)
                                added_videos.append({
                                    'bvid': bvid,
                                    'title': video_title,
                                    'user': uname
                                })
            except Exception as e:
                print(f"检查用户 {uname} 动态时出错: {e}")
        
        return jsonify({
            'success': True,
            'message': f'成功添加 {len(added_videos)} 个视频',
            'added': added_videos
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- Cookie检查API ---

@app.route('/api/cookie-status', methods=['GET'])
def get_cookie_status():
    """获取Cookie状态"""
    try:
        import cookie_checker
        from main import get_header
        
        header = get_header()
        result = cookie_checker.get_cookie_expiry_info(header)
        
        # 尝试解析过期时间
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
        
        # 验证Cookie格式
        if not cookie.startswith('SESSDATA='):
            cookie = 'SESSDATA=' + cookie
        
        # 保存到文件
        with open('bili_cookie.txt', 'w', encoding='utf-8') as f:
            f.write(cookie)
        
        # 验证Cookie是否有效
        import cookie_checker
        from main import get_header
        header = get_header()
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


# --- 扫码登录API ---

# 全局登录管理器
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
    app.run(host='0.0.0.0', port=5000, debug=True)
