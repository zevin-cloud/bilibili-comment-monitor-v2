# filename: database.py
import sqlite3
import datetime

DB_NAME = 'bilibili_monitor.db'

def init_db():
    """初始化數據庫，創建所需的表格（如果它們不存在的話）。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # 創建影片表格
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            oid TEXT PRIMARY KEY,
            bv_id TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        # 創建已見評論表格
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS seen_comments (
            rpid TEXT PRIMARY KEY,
            oid TEXT NOT NULL,
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (oid) REFERENCES videos (oid) ON DELETE CASCADE
        )
        ''')
        # 為 oid 創建索引以加速查詢
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_oid ON seen_comments (oid)')
        
        # 創建監控用戶表格（用於指定用戶評論監控和動態監控）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitored_users (
            mid TEXT PRIMARY KEY,
            uname TEXT NOT NULL,
            monitor_comments INTEGER DEFAULT 1,
            monitor_dynamic INTEGER DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 創建動態視頻記錄表格（記錄已從用戶動態獲取的視頻，避免重複添加）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS dynamic_videos (
            bv_id TEXT PRIMARY KEY,
            mid TEXT NOT NULL,
            title TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mid) REFERENCES monitored_users (mid) ON DELETE CASCADE
        )
        ''')
        
        # 創建監控時間段配置表格
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            days_of_week TEXT NOT NULL,
            interval_seconds INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 插入默認時間段配置（工作日8:00-15:00，30秒一次）
        cursor.execute('''
        INSERT OR IGNORE INTO monitor_schedule (id, name, start_time, end_time, days_of_week, interval_seconds)
        VALUES (1, '工作日高峰時段', '08:00', '15:00', '1,2,3,4,5', 30)
        ''')
        
        # 插入默認時間段配置（其他時間，5分鐘一次）
        cursor.execute('''
        INSERT OR IGNORE INTO monitor_schedule (id, name, start_time, end_time, days_of_week, interval_seconds)
        VALUES (2, '其他時間', '00:00', '23:59', '0,1,2,3,4,5,6', 300)
        ''')
        
        # 創建系統配置表格
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 插入默認配置：是否自動添加用戶動態視頻到監控列表
        cursor.execute('''
        INSERT OR IGNORE INTO system_settings (key, value)
        VALUES ('auto_add_user_videos', '1')
        ''')
        
        conn.commit()

def get_monitored_videos():
    """從數據庫獲取所有正在監控的影片列表。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT oid, bv_id, title FROM videos ORDER BY added_at DESC')
        return cursor.fetchall()

def add_video_to_db(oid, bv_id, title):
    """將一個新影片添加到數據庫。"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO videos (oid, bv_id, title) VALUES (?, ?, ?)', (oid, bv_id, title))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        print(f"提示：影片 {bv_id} ({title}) 已經在數據庫中。")
        return False

def remove_video_from_db(oid):
    """從數據庫中移除一個影片及其所有相關的已見評論。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM videos WHERE oid = ?', (oid,))
        conn.commit()
        return cursor.rowcount > 0

def load_seen_comments_for_video(oid):
    """為給定的影片加載所有已見評論的 rpid 到一個集合中。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT rpid FROM seen_comments WHERE oid = ?', (oid,))
        return {row[0] for row in cursor.fetchall()}

def add_comment_to_db(rpid, oid):
    """將一個新的已見評論 rpid 添加到數據庫。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO seen_comments (rpid, oid) VALUES (?, ?)', (rpid, oid))
        conn.commit()


# --- 用戶監控相關函數 ---

def add_monitored_user(mid, uname, monitor_comments=1, monitor_dynamic=1):
    """添加一個監控用戶到數據庫。"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO monitored_users 
                (mid, uname, monitor_comments, monitor_dynamic) 
                VALUES (?, ?, ?, ?)
            ''', (mid, uname, monitor_comments, monitor_dynamic))
            conn.commit()
            return True
    except Exception as e:
        print(f"添加監控用戶時出錯: {e}")
        return False

def remove_monitored_user(mid):
    """從數據庫中移除一個監控用戶。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM monitored_users WHERE mid = ?', (mid,))
        conn.commit()
        return cursor.rowcount > 0

def get_monitored_users():
    """獲取所有監控用戶列表。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT mid, uname, monitor_comments, monitor_dynamic 
            FROM monitored_users ORDER BY added_at DESC
        ''')
        return cursor.fetchall()

def get_comment_monitored_user_mids():
    """獲取只監控評論的用戶ID集合。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT mid FROM monitored_users WHERE monitor_comments = 1')
        return {row[0] for row in cursor.fetchall()}

def get_dynamic_monitored_user_mids():
    """獲取需要監控動態的用戶ID集合。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT mid, uname FROM monitored_users WHERE monitor_dynamic = 1')
        return {row[0]: row[1] for row in cursor.fetchall()}

def update_user_monitor_settings(mid, monitor_comments=None, monitor_dynamic=None):
    """更新用戶的監控設置。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if monitor_comments is not None:
            cursor.execute('UPDATE monitored_users SET monitor_comments = ? WHERE mid = ?', 
                         (monitor_comments, mid))
        if monitor_dynamic is not None:
            cursor.execute('UPDATE monitored_users SET monitor_dynamic = ? WHERE mid = ?', 
                         (monitor_dynamic, mid))
        conn.commit()
        return cursor.rowcount > 0


# --- 動態視頻相關函數 ---

def add_dynamic_video(bv_id, mid, title):
    """記錄已從用戶動態獲取的視頻。"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO dynamic_videos (bv_id, mid, title) VALUES (?, ?, ?)', 
                         (bv_id, mid, title))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"添加動態視頻記錄時出錯: {e}")
        return False

def get_dynamic_video_bvids():
    """獲取所有已從動態添加的視頻BV號集合。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT bv_id FROM dynamic_videos')
        return {row[0] for row in cursor.fetchall()}

def get_user_dynamic_videos(mid):
    """獲取指定用戶的所有動態視頻。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT bv_id, title FROM dynamic_videos WHERE mid = ?', (mid,))
        return cursor.fetchall()


# --- 監控時間段配置相關函數 ---

def get_monitor_schedules():
    """獲取所有監控時間段配置。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, start_time, end_time, days_of_week, interval_seconds, is_active
            FROM monitor_schedule ORDER BY id
        ''')
        return cursor.fetchall()

def add_monitor_schedule(name, start_time, end_time, days_of_week, interval_seconds):
    """添加新的監控時間段配置。"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO monitor_schedule (name, start_time, end_time, days_of_week, interval_seconds)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, start_time, end_time, days_of_week, interval_seconds))
            conn.commit()
            return True
    except Exception as e:
        print(f"添加時間段配置時出錯: {e}")
        return False

def update_monitor_schedule(schedule_id, **kwargs):
    """更新監控時間段配置。"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            fields = []
            values = []
            for key, value in kwargs.items():
                fields.append(f"{key} = ?")
                values.append(value)
            if fields:
                values.append(schedule_id)
                cursor.execute(f'''
                    UPDATE monitor_schedule SET {', '.join(fields)} WHERE id = ?
                ''', values)
                conn.commit()
                return True
    except Exception as e:
        print(f"更新時間段配置時出錯: {e}")
        return False

def delete_monitor_schedule(schedule_id):
    """刪除監控時間段配置。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM monitor_schedule WHERE id = ?', (schedule_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_current_interval():
    """
    根據當前時間獲取應該的監控間隔（秒）。
    返回 (interval_seconds, schedule_name) 或默認值 (300, '默認')
    """
    now = datetime.datetime.now()
    current_time = now.strftime('%H:%M')
    current_weekday = now.weekday()  # 0=周一, 6=周日
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT interval_seconds, name FROM monitor_schedule
            WHERE is_active = 1
            AND start_time <= ? AND end_time >= ?
        ''', (current_time, current_time))
        
        schedules = cursor.fetchall()
        
        for interval, name in schedules:
            # 檢查星期幾
            cursor.execute('''
                SELECT days_of_week FROM monitor_schedule
                WHERE name = ? AND is_active = 1
            ''', (name,))
            result = cursor.fetchone()
            if result:
                days = [int(d) for d in result[0].split(',')]
                # 轉換星期：Python weekday() 0=周一，但數據庫中 0=周日, 1=周一
                db_weekday = (current_weekday + 1) % 7
                if db_weekday in days:
                    return interval, name
    
    return 300, '默認(5分鐘)'


# --- 系統設置相關函數 ---

def get_system_setting(key, default=None):
    """獲取系統設置值。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM system_settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        return result[0] if result else default

def set_system_setting(key, value):
    """設置系統設置值。"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, str(value)))
            conn.commit()
            return True
    except Exception as e:
        print(f"設置系統配置時出錯: {e}")
        return False

def get_all_settings():
    """獲取所有系統設置。"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM system_settings')
        return {row[0]: row[1] for row in cursor.fetchall()}

