import cookie_checker
from main import get_header

header = get_header()
result = cookie_checker.get_cookie_expiry_info(header)
print(f"Cookie有效: {result.get('valid')}")
print(f"消息: {result.get('message')}")
if result.get('user_info'):
    print(f"用户信息: {result['user_info']}")
