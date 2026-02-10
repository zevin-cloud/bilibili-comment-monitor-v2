from main import get_header, get_information

header = get_header()
bvid = 'BV1mg4y13713'

print(f'正在获取视频 {bvid} 的信息...')
oid, title = get_information(bvid, header)
print(f'OID: {oid}')
print(f'标题: {title}')
