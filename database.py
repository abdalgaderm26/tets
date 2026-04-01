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
            is_banned INTEGER DEFAULT 0,
            joined_at TEXT
        )
    """)
    
    # Check if is_banned exists (Migration)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Already exists
        
    # Admin Audit Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target_user_id INTEGER,
            timestamp TEXT
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
            screenshot_unique_id TEXT,
            status TEXT DEFAULT 'pending',
            submitted_at TEXT
        )
    """)
    
    # Migration: Add screenshot_unique_id if it doesn't exist
    try:
        cursor.execute("ALTER TABLE user_tasks ADD COLUMN screenshot_unique_id TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
    # Create Withdrawals Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            method TEXT,
            details TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    
    # --- NEW PROFESSIONAL TABLES ---
    
    # Settings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Point Packages (Store)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS point_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            points INTEGER,
            price REAL,
            currency TEXT,
            instructions TEXT
        )
    """)
    
    # Transactions (History)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            type TEXT, 
            description TEXT,
            created_at TEXT
        )
    """)
    
    # User Campaigns (Promotion)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            task_type TEXT,
            budget INTEGER,
            reward_per_action INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    
    # Deposits (Buy Points)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            package_id INTEGER,
            screenshot_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    
    # Initialize Default Settings if not exist
    defaults = [
        ('google_api_key', 'AIzaSyBANNn8byDuYUXpc6cIDdCKXCKuFITfcmk'),
        ('min_withdraw', '500'),
        ('referral_v1_reward', '5'),
        ('referral_v2_reward', '2'),
        ('commission_pct', '20'), # Commission taken from user promotions
        ('bankak_details', 'حول إلى بنكك: 1234567\nالاسم: محمد علي'),
        ('fauwri_details', 'حول عبر فوري: 0912345678')
    ]
    for key, val in defaults:
        cursor.execute("INSERT OR IGNORE INTO settings (id, value) VALUES (?, ?)", (key, val))

    conn.commit()
    conn.close()

# --- SETTINGS GETTER/SETTER ---

def get_setting(key, default=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE id = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else default

def set_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (id, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def log_transaction(user_id, amount, t_type, description):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO transactions (user_id, amount, type, description, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, amount, t_type, description, now))
    conn.commit()
    conn.close()

def get_transactions(user_id, limit=10):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    res = cursor.fetchall()
    conn.close()
    return res

# --- SECURITY & BAN SYSTEM ---

def is_user_banned(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] == 1 if res else False

def ban_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def log_admin_action(admin_id, action, target_user_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO admin_logs (admin_id, action, target_user_id, timestamp)
        VALUES (?, ?, ?, ?)
    """, (admin_id, action, target_user_id, now))
    conn.commit()
    conn.close()

def get_admin_logs(limit=20):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_logs ORDER BY id DESC LIMIT ?", (limit,))
    res = cursor.fetchall()
    conn.close()
    return res

# --- SHOP & PACKAGES ---

def add_package(points, price, currency, instructions):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO point_packages (points, price, currency, instructions)
        VALUES (?, ?, ?, ?)
    """, (points, price, currency, instructions))
    conn.commit()
    conn.close()

def get_currencies():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT currency FROM point_packages")
    res = cursor.fetchall()
    conn.close()
    return [c[0] for c in res]

def get_packages_by_currency(currency):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM point_packages WHERE currency = ?", (currency,))
    res = cursor.fetchall()
    conn.close()
    return res

def get_package_by_id(package_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM point_packages WHERE id = ?", (package_id,))
    res = cursor.fetchone()
    conn.close()
    return res

def add_deposit_request(user_id, package_id, screenshot_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO deposits (user_id, package_id, screenshot_id, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
    """, (user_id, package_id, screenshot_id, created_at))
    conn.commit()
    conn.close()

def get_next_pending_deposit():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deposits WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
    res = cursor.fetchone()
    conn.close()
    return res

def approve_deposit(deposit_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Get details
    cursor.execute("SELECT user_id, package_id FROM deposits WHERE id = ?", (deposit_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        return False
    user_id, package_id = res
    # Get points
    cursor.execute("SELECT points FROM point_packages WHERE id = ?", (package_id,))
    points = cursor.fetchone()[0]
    # Update
    cursor.execute("UPDATE deposits SET status = 'approved' WHERE id = ?", (deposit_id,))
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
    conn.commit()
    conn.close()
    return user_id, points

# --- CAMPAIGNS (PROMOTION) ---

def add_campaign(user_id, url, budget, reward, task_type):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Check budget
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res or res[0] < budget:
        conn.close()
        return False
    
    # Deduct
    cursor.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (budget, user_id))
    
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO user_campaigns (user_id, url, task_type, budget, reward_per_action, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (user_id, url, task_type, budget, reward, created_at))
    conn.commit()
    conn.close()
    return True

def get_next_pending_campaign():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_campaigns WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
    res = cursor.fetchone()
    conn.close()
    return res

def approve_campaign(campaign_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Get info
    cursor.execute("SELECT user_id, url, task_type, reward_per_action, budget FROM user_campaigns WHERE id = ?", (campaign_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        return False
        
    uid, url, ttype, reward, budget = res
    total_needed = budget // reward
    
    # Update campaign status
    cursor.execute("UPDATE user_campaigns SET status = 'approved' WHERE id = ?", (campaign_id,))
    
    # Add as a real task for others
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO tasks (url, task_type, reward, total_needed, completed_count, status, created_at)
        VALUES (?, ?, ?, ?, 0, 1, ?)
    """, (url, ttype, reward, total_needed, created_at))
    
    conn.commit()
    conn.close()
    return uid, url

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

def get_available_tasks(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Get active tasks that:
    # 1. Have status = 1
    # 2. Haven't reached their completion limit
    # 3. User hasn't already submitted proof for (regardless of pending/approved/rejected)
    cursor.execute("""
        SELECT * FROM tasks 
        WHERE status = 1 
        AND completed_count < total_needed
        AND id NOT IN (SELECT task_id FROM user_tasks WHERE user_id = ?)
    """, (user_id,))
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

def submit_proof(user_id, task_id, screenshot_id, screenshot_unique_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 1. Check if user already submitted for this task
    cursor.execute("SELECT id FROM user_tasks WHERE user_id = ? AND task_id = ?", (user_id, task_id))
    if cursor.fetchone():
        conn.close()
        return "ALREADY_SUBMITTED"
    
    # 2. Check if this exact photo was used before by ANYONE (Anti-Fraud)
    cursor.execute("SELECT id FROM user_tasks WHERE screenshot_unique_id = ?", (screenshot_unique_id,))
    if cursor.fetchone():
        conn.close()
        return "DUPLICATE_PHOTO"
        
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO user_tasks (user_id, task_id, screenshot_id, screenshot_unique_id, submitted_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, task_id, screenshot_id, screenshot_unique_id, submitted_at))
    sub_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return sub_id

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
    reward_res = cursor.fetchone()
    if not reward_res:
        conn.close()
        return False
    reward = reward_res[0]
    
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

# --- WITHDRAWAL FUNCTIONS ---

def add_withdrawal_request(user_id, amount, method, details):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Check if user has enough points
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res or res[0] < amount:
        conn.close()
        return False
        
    # Deduct points immediately (pending)
    cursor.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (amount, user_id))
    
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO withdrawals (user_id, amount, method, details, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
    """, (user_id, amount, method, details, created_at))
    
    conn.commit()
    conn.close()
    return True

def get_withdrawal_by_id(withdrawal_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
    withd = cursor.fetchone()
    conn.close()
    return withd

def approve_withdrawal(withdrawal_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE withdrawals SET status = 'approved' WHERE id = ?", (withdrawal_id,))
    cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id = ?", (withdrawal_id,))
    res = cursor.fetchone()
    conn.commit()
    conn.close()
    return res

def reject_withdrawal(withdrawal_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get details for refund
    cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id = ?", (withdrawal_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        return False
        
    user_id, amount = res
    
    # Update status to rejected
    cursor.execute("UPDATE withdrawals SET status = 'rejected' WHERE id = ?", (withdrawal_id,))
    # Refund points
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, user_id))
    
    conn.commit()
    conn.close()
    return user_id, amount

def get_pending_counts():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_tasks WHERE status = 'pending'")
    task_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'")
    withd_count = cursor.fetchone()[0]
    conn.close()
    return task_count, withd_count

def get_next_pending_task():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_tasks WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
    task = cursor.fetchone()
    conn.close()
    return task

def get_next_pending_withdrawal():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
    withd = cursor.fetchone()
    conn.close()
    return withd
