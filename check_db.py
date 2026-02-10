import sqlite3

conn = sqlite3.connect('bilibili_monitor.db')
cursor = conn.cursor()

print('所有时间表:')
cursor.execute('SELECT * FROM monitor_schedule')
for row in cursor.fetchall():
    print(f'  {row}')

print()
print('当前时间:', __import__('datetime').datetime.now().strftime('%H:%M'))

# 检查当前应该生效的时间表
now = __import__('datetime').datetime.now()
current_time = now.strftime('%H:%M')
current_weekday = now.weekday()
db_weekday = (current_weekday + 1) % 7

print(f'当前星期(数据库格式): {db_weekday}')

cursor.execute('''
    SELECT interval_seconds, name, start_time, end_time, days_of_week 
    FROM monitor_schedule 
    WHERE is_active = 1 AND start_time <= ? AND end_time >= ?
''', (current_time, current_time))

schedules = cursor.fetchall()
print(f'\n匹配时间段的 schedules: {len(schedules)}')
for s in schedules:
    print(f'  {s}')
    days = [int(d) for d in s[4].split(',')]
    if db_weekday in days:
        print(f'    -> 当前生效: {s[1]} ({s[0]}秒)')

conn.close()
