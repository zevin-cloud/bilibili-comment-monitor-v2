from main import get_header
import user_monitor

header = get_header()
mid = '349490448'

# 获取用户信息
print('获取用户信息...')
uname, face = user_monitor.get_user_info(mid, header)
print(f'用户名: {uname}')
print(f'头像: {face}')

print()

# 获取用户视频
print('获取用户视频列表...')
videos = user_monitor.get_user_dynamic_videos(mid, header, limit=20)
print(f'获取到 {len(videos)} 个视频:')
for bvid, title in videos:
    print(f'  - {bvid}: {title}')
