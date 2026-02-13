# filename: cookie_checker.py
import requests
import time
import urllib.parse

def check_cookie_valid(header):
    """
    检查Cookie是否有效
    
    Returns:
        (is_valid, user_info) - 是否有效，用户信息
    """
    try:
        # 尝试访问B站API获取用户信息
        url = "https://api.bilibili.com/x/web-interface/nav"
        response = requests.get(url, headers=header, timeout=10)
        data = response.json()
        
        if data.get('code') == 0:
            # Cookie有效
            user_data = data.get('data', {})
            user_info = {
                'is_login': user_data.get('isLogin', False),
                'uname': user_data.get('uname', ''),
                'mid': user_data.get('mid', ''),
                'face': user_data.get('face', ''),
                'level': user_data.get('level_info', {}).get('current_level', 0)
            }
            return True, user_info
        else:
            # Cookie无效或过期
            return False, {'error': data.get('message', 'Cookie无效')}
    except Exception as e:
        return False, {'error': str(e)}

def get_cookie_expiry_info(header):
    """
    获取Cookie过期信息
    
    Returns:
        dict: 包含过期时间等信息的字典
    """
    try:
        is_valid, user_info = check_cookie_valid(header)
        
        result = {
            'valid': is_valid,
            'message': ''
        }
        
        if is_valid:
            result['message'] = f"✅ Cookie有效 - 用户: {user_info.get('uname', '未知')}, 等级: LV{user_info.get('level', 0)}"
            result['user_info'] = user_info
        else:
            error_msg = user_info.get('error', '未知错误')
            result['message'] = f"❌ Cookie无效 - {error_msg}"
        
        return result
    except Exception as e:
        return {
            'valid': False,
            'message': f"❌ 检查Cookie时出错: {str(e)}"
        }

def parse_sessdata_expiry(sessdata):
    """
    尝试从SESSDATA解析过期时间
    SESSDATA格式: xxxxxx%2Ctimestamp%2Cxxxxx
    中间的timestamp是Unix时间戳
    """
    try:
        # URL解码
        decoded = urllib.parse.unquote(sessdata)
        parts = decoded.split(',')
        
        if len(parts) >= 2:
            # 第二部分通常是时间戳
            timestamp = int(parts[1])
            expiry_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
            remaining = timestamp - int(time.time())
            
            days = remaining // 86400
            hours = (remaining % 86400) // 3600
            
            return {
                'expiry_timestamp': timestamp,
                'expiry_time': expiry_time,
                'remaining_seconds': remaining,
                'remaining_days': days,
                'remaining_hours': hours,
                'is_expired': remaining <= 0
            }
    except Exception as e:
        pass
    
    return None

if __name__ == "__main__":
    # 测试
    from main import get_header
    header = get_header()
    result = get_cookie_expiry_info(header)
    print(result['message'])
    
    # 尝试解析过期时间
    try:
        with open('bili_cookie.txt', 'r') as f:
            cookie = f.read().strip()
            if cookie.startswith('SESSDATA='):
                sessdata = cookie[9:]  # 去掉 "SESSDATA=" 前缀
                expiry_info = parse_sessdata_expiry(sessdata)
                if expiry_info:
                    if expiry_info['is_expired']:
                        print(f"⚠️ Cookie已过期 ({expiry_info['expiry_time']})")
                    else:
                        print(f"⏰ Cookie将在 {expiry_info['remaining_days']}天 {expiry_info['remaining_hours']}小时后过期")
                        print(f"   过期时间: {expiry_info['expiry_time']}")
    except Exception as e:
        print(f"无法解析过期时间: {e}")
