
import sys
import os
import requests
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.main import get_header

def test_new_detail_api(dynamic_id):
    header = get_header()
    url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id={dynamic_id}"
    resp = requests.get(url, headers=header, timeout=10)
    print(f"Status Code: {resp.status_code}")
    data = resp.json()
    print(f"Code: {data.get('code')}")
    if data.get('code') == 0:
        item = data.get('data', {}).get('item', {})
        print(f"Type: {item.get('type')}")
        modules = item.get('modules', {})
        m_stat = modules.get('module_stat', {})
        print(f"Comment Stat: {m_stat.get('comment')}")
        
        # Bilibili comments OID and Type are usually in the basic or modules
        # For new dynamics, we might need to look into basic or other modules
        basic = item.get('basic', {})
        print(f"Basic: {basic}")
        
        # Let's see the whole item structure for a bit
        print("\nItem Keys:", item.keys())
        if 'modules' in item:
            print("Module Keys:", item['modules'].keys())

if __name__ == "__main__":
    test_new_detail_api("1201745576146763793")
