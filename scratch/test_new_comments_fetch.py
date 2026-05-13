
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.main import get_header
from api.user_monitor import fetch_dynamic_comments

def test_comments():
    header = get_header()
    # 橘子皮要厚 的文章动态
    dynamic_id = "1201745576146763793"
    
    print(f"--- Testing fetch_dynamic_comments for {dynamic_id} (New API) ---")
    result = fetch_dynamic_comments(dynamic_id, header)
    comments = result.get('comments', [])
    print(f"Found {len(comments)} comments.")
    for c in comments:
        print(f"[{c['uname']}]: {c['message']}")
    
    # Also test passing OID/Type directly
    print(f"\n--- Testing fetch_dynamic_comments with direct OID/Type ---")
    # For this dynamic: OID=48970279, Type=12
    result_direct = fetch_dynamic_comments(dynamic_id, header, oid="48970279", comment_type=12)
    comments_direct = result_direct.get('comments', [])
    print(f"Found {len(comments_direct)} comments (direct).")

if __name__ == "__main__":
    test_comments()
