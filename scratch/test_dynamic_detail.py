
import sys
import os
import requests
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.main import get_header

def test_fetch_comments(dynamic_id):
    header = get_header()
    simple_header = {
        'User-Agent': header.get('User-Agent'),
        'Cookie': header.get('Cookie'),
        'Referer': f'https://t.bilibili.com/{dynamic_id}'
    }
    
    print(f"--- Testing fetch_dynamic_detail for ID {dynamic_id} ---")
    url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail"
    params = {'dynamic_id': dynamic_id}
    resp = requests.get(url, headers=simple_header, params=params, timeout=10)
    print(f"Status Code: {resp.status_code}")
    print(f"Response Text (first 500 chars): {resp.text[:500]}")
    
    try:
        data = resp.json()
        print(f"JSON Code: {data.get('code')}")
        if data.get('code') == 0:
            card = data.get('data', {}).get('card', {})
            card_data = json.loads(card) if isinstance(card, str) else card
            desc = card_data.get('desc', {})
            print(f"Dynamic Type: {desc.get('type')}")
            print(f"RID: {desc.get('rid')}")
            print(f"RID STR: {desc.get('rid_str')}")
    except Exception as e:
        print(f"Error parsing JSON: {e}")

if __name__ == "__main__":
    test_fetch_comments("1201745576146763793")
