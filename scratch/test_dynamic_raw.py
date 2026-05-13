import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.main import get_header
import requests
header = get_header()
mid = "349490448" # 橘子皮要厚

url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={mid}"
resp = requests.get(url, headers=header, timeout=10)
data = resp.json()
with open("scratch/space_raw.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

url_feed = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all"
resp_feed = requests.get(url_feed, headers=header, timeout=10)
data_feed = resp_feed.json()
with open("scratch/feed_raw.json", "w", encoding="utf-8") as f:
    json.dump(data_feed, f, ensure_ascii=False, indent=2)

print("Done")
