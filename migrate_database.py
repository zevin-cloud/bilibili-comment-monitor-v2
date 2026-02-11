"""
数据库迁移脚本 - 将旧架构数据迁移到新架构
从分散的 videos/monitored_dynamics 表迁移到统一的 activities 表
"""
import sqlite3
import json
import sys

DB_NAME = 'bilibili_monitor.db'


def migrate_to_unified_activities():
    """
    迁移到统一活动表
    - videos -> activities (type='video')
    - monitored_dynamics -> activities (type='dynamic')
    """
    print("=" * 50)
    print("开始数据迁移到统一活动表...")
    print("=" * 50)
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 检查是否已经迁移过
        cursor.execute('SELECT COUNT(*) FROM activities')
        existing_count = cursor.fetchone()[0]
        if existing_count > 0:
            print(f"activities 表中已有 {existing_count} 条记录，跳过迁移")
            return
        
        # 迁移视频数据
        print("\n[1/2] 迁移视频数据...")
        cursor.execute('''
            SELECT oid, bv_id, title, owner_mid, added_at
            FROM videos
        ''')
        videos = cursor.fetchall()
        
        video_count = 0
        for oid, bv_id, title, owner_mid, added_at in videos:
            extra_data = {'bvid': bv_id}
            try:
                cursor.execute('''
                    INSERT INTO activities 
                    (id, activity_type, owner_mid, owner_name, content, title, extra_data, added_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    oid,
                    'video',
                    owner_mid,
                    None,
                    title,
                    title,
                    json.dumps(extra_data),
                    added_at
                ))
                video_count += 1
            except sqlite3.IntegrityError:
                print(f"  跳过重复视频: {title}")
        
        print(f"  成功迁移 {video_count} 个视频")
        
        # 迁移动态数据
        print("\n[2/2] 迁移动态数据...")
        cursor.execute('''
            SELECT d.dynamic_id, d.mid, d.content, d.dynamic_type, d.added_at, u.uname
            FROM monitored_dynamics d
            LEFT JOIN monitored_users u ON d.mid = u.mid
        ''')
        dynamics = cursor.fetchall()
        
        dynamic_count = 0
        for dynamic_id, mid, content, dynamic_type, added_at, uname in dynamics:
            extra_data = {'dynamic_type': dynamic_type}
            try:
                cursor.execute('''
                    INSERT INTO activities 
                    (id, activity_type, owner_mid, owner_name, content, title, extra_data, added_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    dynamic_id,
                    'dynamic',
                    mid,
                    uname,
                    content,
                    content[:50] if content else '',
                    json.dumps(extra_data),
                    added_at
                ))
                dynamic_count += 1
            except sqlite3.IntegrityError:
                print(f"  跳过重复动态: {dynamic_id}")
        
        print(f"  成功迁移 {dynamic_count} 个动态")
        
        conn.commit()
        print("\n✅ 数据迁移完成！")


def migrate_comments_to_unified():
    """
    迁移评论数据到统一评论表
    - seen_comments -> activity_comments (for videos)
    - seen_dynamic_comments -> activity_comments (for dynamics)
    """
    print("\n" + "=" * 50)
    print("开始数据迁移到统一评论表...")
    print("=" * 50)
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 检查是否已经迁移过
        cursor.execute('SELECT COUNT(*) FROM activity_comments')
        existing_count = cursor.fetchone()[0]
        if existing_count > 0:
            print(f"activity_comments 表中已有 {existing_count} 条记录，跳过迁移")
            return
        
        # 迁移视频评论
        print("\n[1/2] 迁移视频评论...")
        cursor.execute('''
            SELECT sc.rpid, sc.oid, sc.seen_at, v.owner_mid
            FROM seen_comments sc
            LEFT JOIN videos v ON sc.oid = v.oid
        ''')
        video_comments = cursor.fetchall()
        
        video_comment_count = 0
        for rpid, oid, seen_at, owner_mid in video_comments:
            try:
                cursor.execute('''
                    INSERT INTO activity_comments 
                    (rpid, activity_id, activity_type, commenter_mid, commenter_name, content, is_owner, seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rpid,
                    oid,
                    'video',
                    None,
                    None,
                    None,
                    0,
                    seen_at
                ))
                video_comment_count += 1
            except sqlite3.IntegrityError:
                pass
        
        print(f"  成功迁移 {video_comment_count} 条视频评论")
        
        # 迁移动态评论
        print("\n[2/2] 迁移动态评论...")
        cursor.execute('''
            SELECT sdc.rpid, sdc.dynamic_id, sdc.seen_at, d.mid
            FROM seen_dynamic_comments sdc
            LEFT JOIN monitored_dynamics d ON sdc.dynamic_id = d.dynamic_id
        ''')
        dynamic_comments = cursor.fetchall()
        
        dynamic_comment_count = 0
        for rpid, dynamic_id, seen_at, owner_mid in dynamic_comments:
            try:
                cursor.execute('''
                    INSERT INTO activity_comments 
                    (rpid, activity_id, activity_type, commenter_mid, commenter_name, content, is_owner, seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rpid,
                    dynamic_id,
                    'dynamic',
                    None,
                    None,
                    None,
                    0,
                    seen_at
                ))
                dynamic_comment_count += 1
            except sqlite3.IntegrityError:
                pass
        
        print(f"  成功迁移 {dynamic_comment_count} 条动态评论")
        
        conn.commit()
        print("\n✅ 评论数据迁移完成！")


def show_migration_summary():
    """显示迁移摘要"""
    print("\n" + "=" * 50)
    print("迁移摘要")
    print("=" * 50)
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 统计旧表数据
        cursor.execute('SELECT COUNT(*) FROM videos')
        old_video_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM monitored_dynamics')
        old_dynamic_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM seen_comments')
        old_video_comment_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM seen_dynamic_comments')
        old_dynamic_comment_count = cursor.fetchone()[0]
        
        # 统计新表数据
        cursor.execute('SELECT COUNT(*) FROM activities')
        new_activity_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM activity_comments')
        new_comment_count = cursor.fetchone()[0]
        
        print(f"\n旧表数据:")
        print(f"  - videos: {old_video_count}")
        print(f"  - monitored_dynamics: {old_dynamic_count}")
        print(f"  - seen_comments: {old_video_comment_count}")
        print(f"  - seen_dynamic_comments: {old_dynamic_comment_count}")
        
        print(f"\n新表数据:")
        print(f"  - activities: {new_activity_count}")
        print(f"  - activity_comments: {new_comment_count}")
        
        print(f"\n按类型统计 activities:")
        cursor.execute('''
            SELECT activity_type, COUNT(*) 
            FROM activities 
            GROUP BY activity_type
        ''')
        for activity_type, count in cursor.fetchall():
            print(f"  - {activity_type}: {count}")


def main():
    """主函数"""
    print("B站评论监控系统 - 数据库迁移工具")
    print("将旧架构数据迁移到新统一架构\n")
    
    try:
        migrate_to_unified_activities()
        migrate_comments_to_unified()
        show_migration_summary()
        
        print("\n" + "=" * 50)
        print("迁移完成！")
        print("=" * 50)
        print("\n提示：旧表（videos, monitored_dynamics, seen_comments, seen_dynamic_comments）")
        print("      仍然保留，可以安全删除或保留作为备份。")
        
    except Exception as e:
        print(f"\n❌ 迁移过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
