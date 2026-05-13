
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.main import get_header
from api.user_monitor import get_user_dynamics, get_followed_feed

def test_fetch():
    header = get_header()
    mid = "349490448" # 橘子皮要厚
    
    print(f"--- Testing get_user_dynamics for MID {mid} ---")
    dynamics = get_user_dynamics(mid, header, limit=5)
    for d in dynamics:
        print(f"ID: {d['dynamic_id']}, Type: {d['type']}, Time: {d['timestamp']}")
        content = d['content'][:50].replace('\n', ' ')
        print(f"Content: {content}")
        print(f"Is Exclusive: {d['is_exclusive']}")
        print("-" * 20)
    
    print(f"\n--- Testing get_followed_feed ---")
    feed = get_followed_feed(header, limit=10)
    for f in feed:
        if f['mid'] == mid:
            print(f"MATCH FOUND in FEED:")
            print(f"ID: {f['dynamic_id']}, Type: {f['type']}, User: {f['uname']}")
            content = f['content'][:50].replace('\n', ' ')
            print(f"Content: {content}")
            print(f"Is Exclusive: {f['is_exclusive']}")
            print("-" * 20)

if __name__ == "__main__":
    test_fetch()
