
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.main import get_header
import requests

def test_feed_content():
    header = get_header()
    mid = "349490448"
    url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={mid}"
    resp = requests.get(url, headers=header, timeout=10)
    data = resp.json()
    if data.get('code') == 0:
        items = data.get('data', {}).get('items', [])
        for item in items[:3]:
            print(f"Dynamic ID: {item.get('id_str')}")
            print(f"Type: {item.get('type')}")
            basic = item.get('basic', {})
            print(f"Comment OID: {basic.get('comment_id_str')}")
            print(f"Comment Type: {basic.get('comment_type')}")
            print("-" * 20)

if __name__ == "__main__":
    test_feed_content()
