import sys, os, json
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.main import get_header

def test_fetch():
    header = get_header()
    mid = "550494308" # 卢本圆复盘
    
    # Check space
    space_url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={mid}"
    resp_space = requests.get(space_url, headers=header, timeout=10)
    data_space = resp_space.json()
    
    print("--- Space Dynamics ---")
    for item in data_space.get('data', {}).get('items', []):
        id_str = item.get('id_str')
        type_str = item.get('type')
        is_only_fans = item.get('basic', {}).get('is_only_fans')
        content = item.get('modules', {}).get('module_dynamic', {}).get('desc', {}).get('text', '')
        if not content:
            content = item.get('modules', {}).get('module_dynamic', {}).get('major', {}).get('opus', {}).get('summary', {}).get('text', '')
        print(f"ID: {id_str}, Type: {type_str}, OnlyFans: {is_only_fans}, Content: {content[:20].replace(chr(10), ' ')}")

    # Check feed
    feed_url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all"
    resp_feed = requests.get(feed_url, headers=header, timeout=10)
    data_feed = resp_feed.json()
    
    print("\n--- Feed Dynamics ---")
    for item in data_feed.get('data', {}).get('items', []):
        id_str = item.get('id_str')
        type_str = item.get('type')
        uname = item.get('modules', {}).get('module_author', {}).get('name')
        is_only_fans = item.get('basic', {}).get('is_only_fans')
        if uname in ["卢本圆复盘", "笨笨的韭菜", "橘子皮要厚"]:
            content = item.get('modules', {}).get('module_dynamic', {}).get('desc', {}).get('text', '')
            if not content:
                content = item.get('modules', {}).get('module_dynamic', {}).get('major', {}).get('opus', {}).get('summary', {}).get('text', '')
            print(f"User: {uname}, ID: {id_str}, Type: {type_str}, OnlyFans: {is_only_fans}, Content: {content[:20].replace(chr(10), ' ')}")

if __name__ == "__main__":
    test_fetch()
