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
    
    # Create Tasks Table (TikTok Tasks)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            task_type TEXT,
            reward INTEGER,
            total_needed INTEGER,
            completed_count INTEGER DEFAULT 0,
            status INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)
    
    # Create User Tasks Table (Submissions)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_id INTEGER,
            screenshot_id TEXT,
            status TEXT DEFAULT 'pending',
            submitted_at TEXT
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

# --- TASK MANAGEMENT FUNCTIONS ---

def add_task(url, task_type, reward, total_needed):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO tasks (url, task_type, reward, total_needed, completed_count, status, created_at)
        VALUES (?, ?, ?, ?, 0, 1, ?)
    """, (url, task_type, reward, total_needed, created_at))
    conn.commit()
    conn.close()

def get_available_tasks():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM tasks 
        WHERE status = 1 AND completed_count < total_needed
    """)
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_task_by_id(task_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    conn.close()
    return task

def submit_proof(user_id, task_id, screenshot_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Check if user already submitted for this task
    cursor.execute("SELECT id FROM user_tasks WHERE user_id = ? AND task_id = ?", (user_id, task_id))
    if cursor.fetchone():
        conn.close()
        return False
        
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO user_tasks (user_id, task_id, screenshot_id, submitted_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, task_id, screenshot_id, submitted_at))
    conn.commit()
    conn.close()
    return True

def approve_submission(submission_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get submission details
    cursor.execute("SELECT user_id, task_id FROM user_tasks WHERE id = ?", (submission_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        return False
        
    user_id, task_id = res
    
    # Get reward amount
    cursor.execute("SELECT reward FROM tasks WHERE id = ?", (task_id,))
    reward = cursor.fetchone()[0]
    
    # Update status to approved
    cursor.execute("UPDATE user_tasks SET status = 'approved' WHERE id = ?", (submission_id,))
    # Add points to user
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (reward, user_id))
    # Increment completed_count in tasks
    cursor.execute("UPDATE tasks SET completed_count = completed_count + 1 WHERE id = ?", (task_id,))
    
    conn.commit()
    conn.close()
    return user_id, reward

def reject_submission(submission_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get user_id for notification
    cursor.execute("SELECT user_id FROM user_tasks WHERE id = ?", (submission_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        return False
        
    user_id = res[0]
    
    # Update status to rejected
    cursor.execute("UPDATE user_tasks SET status = 'rejected' WHERE id = ?", (submission_id,))
    conn.commit()
    conn.close()
    return user_id

def get_submission_by_id(submission_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_tasks WHERE id = ?", (submission_id,))
    sub = cursor.fetchone()
    conn.close()
    return sub
