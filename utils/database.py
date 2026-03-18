import sqlite3
import os
import datetime
import time
from pathlib import Path
import logging

logger = logging.getLogger("MediaBot")

# Default database path - can be overridden
DB_FILE = os.getenv("DATABASE_PATH", "history.db")

def set_db_path(path):
    """Set custom database path before any operations."""
    global DB_FILE
    DB_FILE = path
    # Ensure directory exists
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

def _get_db_connection():
    """Get a database connection with proper error handling."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_db():
    """Initialize database with proper schema."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        # Downloads table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                url TEXT NOT NULL,
                format TEXT,
                size_mb REAL,
                download_date TEXT,
                user_id INTEGER
            )
        ''')
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                usage_count INTEGER DEFAULT 0,
                last_used REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for common queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_download_date ON downloads(download_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON downloads(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_last_used ON users(last_used)')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

def check_rate_limit(user_id, username, limit_per_min=5):
    """Check if user has exceeded rate limit and update tracking."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        now_ts = time.time()
        
        cursor.execute('SELECT usage_count, last_used FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute(
                'INSERT INTO users (user_id, username, usage_count, last_used) VALUES (?, ?, 1, ?)', 
                (user_id, username, now_ts)
            )
            conn.commit()
            conn.close()
            return True, 0
        
        count, last_used = row
        # Reset count if it's been over a minute since last use
        if now_ts - last_used > 60:
            cursor.execute(
                'UPDATE users SET usage_count = 1, last_used = ?, username = ? WHERE user_id = ?', 
                (now_ts, username, user_id)
            )
            conn.commit()
            conn.close()
            return True, 0
        elif count >= limit_per_min:
            conn.close()
            return False, int(60 - (now_ts - last_used))  # Return False and wait time
        else:
            cursor.execute(
                'UPDATE users SET usage_count = usage_count + 1, last_used = ?, username = ? WHERE user_id = ?', 
                (now_ts, username, user_id)
            )
            conn.commit()
            conn.close()
            return True, 0
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        return True, 0  # Allow on error to prevent service disruption

def get_stats():
    """Get bot statistics safely."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM downloads')
        tot_downloads = cursor.fetchone()[0] or 0
        cursor.execute('SELECT COUNT(*) FROM users')
        tot_users = cursor.fetchone()[0] or 0
        conn.close()
        return tot_downloads, tot_users
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return 0, 0

def add_download_record(filename, url, format_type, size_bytes, user_id=None):
    """Add download record with proper validation."""
    try:
        size_mb = size_bytes / (1024 * 1024) if size_bytes else 0
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Sanitize filename to prevent path traversal
        filename = os.path.basename(filename)
        
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO downloads (filename, url, format, size_mb, download_date, user_id)
               VALUES (?, ?, ?, ?, ?, ?)''', 
            (filename, url, format_type, size_mb, date_str, user_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Download recorded: {filename} ({format_type})")
    except Exception as e:
        logger.error(f"Error adding download record: {e}")

def get_recent_downloads(limit=50):
    """Get recent downloads with limit."""
    try:
        if limit > 1000:
            limit = 1000  # Prevent excessive queries
        
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT filename, url, format, size_mb, download_date 
               FROM downloads 
               ORDER BY id DESC LIMIT ?''', 
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Error getting recent downloads: {e}")
        return []

def clear_history():
    """Clear download history with logging."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM downloads')
        conn.commit()
        conn.close()
        logger.warning("Download history cleared")
    except Exception as e:
        logger.error(f"Error clearing history: {e}")

def get_recent_users(limit=15):
    """Get recent users with limit."""
    try:
        if limit > 1000:
            limit = 1000  # Prevent excessive queries
        
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT user_id, username, usage_count, last_used 
               FROM users 
               ORDER BY last_used DESC LIMIT ?''', 
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return []
