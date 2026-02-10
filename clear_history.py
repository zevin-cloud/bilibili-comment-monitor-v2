import database as db
import sqlite3

# 连接数据库
conn = sqlite3.connect(db.DB_NAME)
cursor = conn.cursor()

# 清空视频的评论记录
oid = '824279272'
cursor.execute('DELETE FROM seen_comments WHERE oid = ?', (oid,))
conn.commit()

# 检查
seen = db.load_seen_comments_for_video(oid)
print(f'清空后，视频 {oid} 有 {len(seen)} 条历史评论')

conn.close()
