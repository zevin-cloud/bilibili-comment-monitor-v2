from main import get_header, fetch_latest_comments

header = get_header()
oid = '824279272'  # 正确的OID

print(f'正在获取视频 {oid} 的评论...')
comments = fetch_latest_comments(oid, header)
print(f'获取到 {len(comments)} 条顶层评论')

for i, c in enumerate(comments[:10]):
    uname = c['member']['uname']
    msg = c['content']['message'][:50]
    rpid = c['rpid_str']
    print(f'{i+1}. [{uname}]: {msg}...')
    print(f'   rpid: {rpid}')
