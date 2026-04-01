import sqlite3
from datetime import datetime, timedelta

DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 10,
            referred_by INTEGER,
            last_daily TEXT,
            is_admin INTEGER DEFAULT 0,
            joined_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def register_user(user_id, username, referred_by=None, initial_points=10):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if user already exists
    if get_user(user_id):
        conn.close()
        return False
        
    joined_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO users (user_id, username, points, referred_by, joined_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, initial_points, referred_by, joined_at))
    
    conn.commit()
    conn.close()
    return True

def add_points(user_id, points):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
    conn.commit()
    conn.close()

def deduct_points(user_id, points):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (points, user_id))
    conn.commit()
    conn.close()

def can_claim_daily(user_id):
    user = get_user(user_id)
    if not user or not user[4]: # last_daily column
        return True
    
    last_daily = datetime.strptime(user[4], "%Y-%m-%d %H:%M:%S")
    time_diff = datetime.now() - last_daily
    return time_diff >= timedelta(hours=24)

def update_daily_claim(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (now, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(points) FROM users")
    stats = cursor.fetchone()
    conn.close()
    return stats
