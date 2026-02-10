import requests

r = requests.get('http://127.0.0.1:5000/api/logs')
data = r.json()
print(f'日志行数: {len(data.get("logs", []))}')
print('最近10行日志:')
for line in data.get('logs', [])[-10:]:
    print(line)
