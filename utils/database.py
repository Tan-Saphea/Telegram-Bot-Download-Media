import sqlite3
import os
import datetime
import time

DB_FILE = "history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Downloads table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            url TEXT,
            format TEXT,
            size_mb REAL,
            download_date TEXT
        )
    ''')
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            usage_count INTEGER DEFAULT 0,
            last_used REAL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def check_rate_limit(user_id, username, limit_per_min=5):
    """Check if user has exceeded rate limit and update tracking."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now_ts = time.time()
    
    cursor.execute('SELECT usage_count, last_used FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute('INSERT INTO users (user_id, username, usage_count, last_used) VALUES (?, ?, 1, ?)', 
                       (user_id, username, now_ts))
        conn.commit()
        conn.close()
        return True, 0
    
    count, last_used = row
    # Reset count if it's been over a minute since last use
    if now_ts - last_used > 60:
        cursor.execute('UPDATE users SET usage_count = 1, last_used = ?, username = ? WHERE user_id = ?', 
                       (now_ts, username, user_id))
        conn.commit()
        conn.close()
        return True, 0
    elif count >= limit_per_min:
        conn.close()
        return False, int(60 - (now_ts - last_used))  # Return False and wait time
    else:
        cursor.execute('UPDATE users SET usage_count = usage_count + 1, last_used = ?, username = ? WHERE user_id = ?', 
                       (now_ts, username, user_id))
        conn.commit()
        conn.close()
        return True, 0

def get_stats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM downloads')
    tot_downloads = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users')
    tot_users = cursor.fetchone()[0]
    conn.close()
    return tot_downloads, tot_users

def add_download_record(filename, url, format_type, size_bytes):
    size_mb = size_bytes / (1024 * 1024) if size_bytes else 0
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO downloads (filename, url, format, size_mb, download_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (filename, url, format_type, size_mb, date_str))
    conn.commit()
    conn.close()

def get_recent_downloads(limit=50):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT filename, url, format, size_mb, download_date 
        FROM downloads 
        ORDER BY id DESC LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def clear_history():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM downloads')
    conn.commit()
    conn.close()

def get_recent_users(limit=15):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, usage_count, last_used 
        FROM users 
        ORDER BY last_used DESC LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows
