# filename: auto_login.py
import requests
import qrcode
import time
import os
import threading
from datetime import datetime, timedelta

# Bilibili API URLs
QR_GENERATE_API = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
QR_POLL_API = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"

class AutoLoginManager:
    """自动登录管理器"""
    
    def __init__(self):
        self.is_logging_in = False
        self.login_callback = None
        self.qrcode_key = None
        self.session = None
        
    def generate_qrcode(self):
        """生成二维码并返回二维码key和图片路径"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            response = requests.get(QR_GENERATE_API, headers=headers)
            data = response.json()
            
            if data['code'] == 0:
                login_url = data['data']['url']
                self.qrcode_key = data['data']['qrcode_key']
                
                # 生成二维码图片
                img = qrcode.make(login_url)
                img_path = "qrcode.png"
                img.save(img_path)
                
                return {
                    'success': True,
                    'qrcode_key': self.qrcode_key,
                    'img_path': img_path,
                    'login_url': login_url
                }
            else:
                return {'success': False, 'error': data.get('message', '获取二维码失败')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def poll_login_status(self, callback=None):
        """轮询登录状态"""
        if not self.qrcode_key:
            return {'success': False, 'error': '未生成二维码'}
        
        self.is_logging_in = True
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        session = requests.Session()
        session.headers.update(headers)
        
        scan_confirmed = False
        start_time = time.time()
        timeout = 180  # 3分钟超时
        
        try:
            while self.is_logging_in and (time.time() - start_time) < timeout:
                poll_url = f"{QR_POLL_API}?qrcode_key={self.qrcode_key}"
                response = session.get(poll_url)
                data = response.json()
                
                status_code = data['data']['code']
                
                if status_code == 0:
                    # 登录成功
                    self.session = session
                    self.is_logging_in = False
                    
                    # 保存cookie
                    self._save_cookie(session)
                    
                    if callback:
                        callback({'success': True, 'message': '登录成功'})
                    return {'success': True, 'message': '登录成功'}
                    
                elif status_code == 86090:
                    if not scan_confirmed:
                        scan_confirmed = True
                        if callback:
                            callback({'success': False, 'message': '已扫描，请确认登录', 'status': 'scanned'})
                            
                elif status_code == 86101:
                    # 等待扫描
                    if callback:
                        callback({'success': False, 'message': '等待扫码...', 'status': 'waiting'})
                        
                elif status_code == 86038:
                    self.is_logging_in = False
                    if callback:
                        callback({'success': False, 'error': '二维码已过期', 'status': 'expired'})
                    return {'success': False, 'error': '二维码已过期'}
                else:
                    self.is_logging_in = False
                    if callback:
                        callback({'success': False, 'error': f'未知错误: {status_code}'})
                    return {'success': False, 'error': f'未知错误: {status_code}'}
                
                time.sleep(2)
            
            # 超时
            self.is_logging_in = False
            if callback:
                callback({'success': False, 'error': '登录超时', 'status': 'timeout'})
            return {'success': False, 'error': '登录超时'}
            
        except Exception as e:
            self.is_logging_in = False
            if callback:
                callback({'success': False, 'error': str(e)})
            return {'success': False, 'error': str(e)}
    
    def _save_cookie(self, session):
        """保存cookie到文件"""
        cookie_dict = session.cookies.get_dict()
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_dict.items()])
        
        with open("bili_cookie.txt", 'w', encoding='utf-8') as f:
            f.write(cookie_str)
    
    def stop_login(self):
        """停止登录"""
        self.is_logging_in = False


def check_and_refresh_cookie():
    """
    检查cookie是否即将过期，如果是则返回需要重新登录的提示
    返回: {'need_refresh': bool, 'message': str, 'days_left': int}
    """
    try:
        import cookie_checker
        from main import get_header
        
        header = get_header()
        result = cookie_checker.get_cookie_expiry_info(header)
        
        if not result.get('valid'):
            return {
                'need_refresh': True,
                'message': 'Cookie已失效，需要重新登录',
                'days_left': 0
            }
        
        # 尝试解析过期时间
        try:
            with open('bili_cookie.txt', 'r') as f:
                cookie = f.read().strip()
                if cookie.startswith('SESSDATA='):
                    sessdata = cookie[9:]
                    expiry_info = cookie_checker.parse_sessdata_expiry(sessdata)
                    if expiry_info:
                        days_left = expiry_info['remaining_days']
                        
                        # 如果剩余天数小于3天，提醒刷新
                        if days_left < 3:
                            return {
                                'need_refresh': True,
                                'message': f'Cookie将在 {days_left} 天后过期，建议重新登录',
                                'days_left': days_left
                            }
                        else:
                            return {
                                'need_refresh': False,
                                'message': f'Cookie有效，还剩 {days_left} 天',
                                'days_left': days_left
                            }
        except:
            pass
        
        return {
            'need_refresh': False,
            'message': 'Cookie有效',
            'days_left': -1
        }
        
    except Exception as e:
        return {
            'need_refresh': True,
            'message': f'检查Cookie失败: {str(e)}',
            'days_left': 0
        }


if __name__ == "__main__":
    # 测试
    result = check_and_refresh_cookie()
    print(result['message'])
