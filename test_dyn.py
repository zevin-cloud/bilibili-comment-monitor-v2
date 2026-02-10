from main import get_header
import user_monitor

header = get_header()
mid = '349490448'

print('获取用户动态...')
dynamics = user_monitor.get_user_dynamics(mid, header, limit=20)
print(f'获取到 {len(dynamics)} 条动态:')
for dyn in dynamics:
    type_name = {
        1: "转发",
        2: "图片",
        4: "文字",
        8: "视频",
        64: "专栏"
    }.get(dyn['type'], f"类型{dyn['type']}")
    print(f'  [{type_name}] {dyn["content"][:30]}... (ID: {dyn["dynamic_id"]})')
