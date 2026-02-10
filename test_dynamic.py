from main import get_header
import user_monitor

header = get_header()
mid = '349490448'

print(f'正在获取用户 {mid} 的动态视频...')
videos = user_monitor.get_user_dynamic_videos(mid, header, limit=10)

print(f'获取到 {len(videos)} 个视频:')
for bvid, title in videos:
    print(f'  - {bvid}: {title}')
