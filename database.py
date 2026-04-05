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
            language TEXT DEFAULT 'ar',
            vip_until TEXT,
            joined_at TEXT
        )
    """)
    
    # Check if new columns exist (Migration)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ar'")
        cursor.execute("ALTER TABLE users ADD COLUMN vip_until TEXT")
    except sqlite3.OperationalError:
        pass # Already exists
    
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
    cursor.execute("INSERT OR IGNORE INTO settings (id, value) VALUES ('usdt_wallet', 'TUL8oVJYogpHPqRKXYmjvTPQhdA9b2vNRC')")
    cursor.execute("INSERT OR IGNORE INTO settings (id, value) VALUES ('vip_multiplier', '2.0')")
    cursor.execute("INSERT OR IGNORE INTO settings (id, value) VALUES ('vip_price', '1000')")
    cursor.execute("INSERT OR IGNORE INTO settings (id, value) VALUES ('maintenance_mode', 'off')")
    
    conn.commit()
    conn.close()

from contextlib import contextmanager
@contextmanager
def get_db_conn():
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
    finally:
        conn.close()

# --- SETTINGS GETTER/SETTER ---

def get_setting(key, default=None):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE id = ?", (key,))
        res = cursor.fetchone()
        return res[0] if res else default

def set_setting(key, value):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (id, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()

def log_transaction(user_id, amount, t_type, description):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO transactions (user_id, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, amount, t_type, description, now))
        conn.commit()

def get_transactions(user_id, limit=10):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        return cursor.fetchall()

# --- SECURITY & BAN SYSTEM ---

def is_user_banned(user_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        return res[0] == 1 if res else False

def ban_user(user_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        conn.commit()

def unban_user(user_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        conn.commit()

def log_admin_action(admin_id, action, target_user_id=None):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO admin_logs (admin_id, action, target_user_id, timestamp)
            VALUES (?, ?, ?, ?)
        """, (admin_id, action, target_user_id, now))
        conn.commit()

def get_admin_logs(limit=20):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin_logs ORDER BY id DESC LIMIT ?", (limit,))
        return cursor.fetchall()

# --- VIP & LANGUAGE HELPERS ---

def is_vip(user_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT vip_until FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        if res and res[0]:
            try:
                vip_date = datetime.strptime(res[0], "%Y-%m-%d %H:%M:%S")
                return datetime.now() < vip_date
            except:
                return False
        return False

def get_user_lang(user_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        return res[0] if res else 'ar'

def set_user_lang(user_id, lang):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        conn.commit()

def set_vip(user_id, days):
    # HIGH-02 FIX: Use context manager instead of raw connection
    with get_db_conn() as conn:
        cursor = conn.cursor()
        expire_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET vip_until = ? WHERE user_id = ?", (expire_date, user_id))
        conn.commit()

# --- SHOP & PACKAGES ---

def add_package(points, price, currency, instructions):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO point_packages (points, price, currency, instructions)
            VALUES (?, ?, ?, ?)
        """, (points, price, currency, instructions))
        conn.commit()

def get_currencies():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT currency FROM point_packages")
        res = cursor.fetchall()
        return [c[0] for c in res]

def get_packages_by_currency(currency):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM point_packages WHERE currency = ?", (currency,))
        return cursor.fetchall()

def get_package_by_id(package_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM point_packages WHERE id = ?", (package_id,))
        return cursor.fetchone()

def add_deposit_request(user_id, package_id, screenshot_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO deposits (user_id, package_id, screenshot_id, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        """, (user_id, package_id, screenshot_id, created_at))
        conn.commit()

def get_next_pending_deposit():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM deposits WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
        return cursor.fetchone()

def approve_deposit(deposit_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        # Get details
        cursor.execute("SELECT user_id, package_id FROM deposits WHERE id = ?", (deposit_id,))
        res = cursor.fetchone()
        if not res:
            return False
        user_id, package_id = res
        # Get points
        cursor.execute("SELECT points FROM point_packages WHERE id = ?", (package_id,))
        points = cursor.fetchone()[0]
        # Update
        cursor.execute("UPDATE deposits SET status = 'approved' WHERE id = ?", (deposit_id,))
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
        conn.commit()
        return user_id, points

# --- CAMPAIGNS (PROMOTION) ---

def add_campaign(user_id, url, budget, reward, task_type):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        # Check budget
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        if not res or res[0] < budget:
            return False
        
        # Deduct
        cursor.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (budget, user_id))
        
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO user_campaigns (user_id, url, task_type, budget, reward_per_action, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (user_id, url, task_type, budget, reward, created_at))
        conn.commit()
        return True

def get_next_pending_campaign():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_campaigns WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
        return cursor.fetchone()

def approve_campaign(campaign_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        # Get info
        cursor.execute("SELECT user_id, url, task_type, reward_per_action, budget FROM user_campaigns WHERE id = ?", (campaign_id,))
        res = cursor.fetchone()
        if not res:
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
        return uid, url

def reject_campaign(campaign_id):
    """CRIT-03 FIX: This function was called in admin_handlers but did not exist."""
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM user_campaigns WHERE id = ?", (campaign_id,))
        res = cursor.fetchone()
        if not res:
            return None
        user_id = res[0]
        cursor.execute("UPDATE user_campaigns SET status = 'rejected' WHERE id = ?", (campaign_id,))
        conn.commit()
        return user_id

def get_user(user_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()

def register_user(user_id, username, referred_by=None, initial_points=10):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            return False
            
        joined_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO users (user_id, username, points, referred_by, joined_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, initial_points, referred_by, joined_at))
        
        conn.commit()
        return True

def add_points(user_id, points):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
        conn.commit()

def deduct_points(user_id, points):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (points, user_id))
        conn.commit()

def can_claim_daily(user_id):
    user = get_user(user_id)
    if not user or not user[4]: # last_daily column
        return True
    
    last_daily = datetime.strptime(user[4], "%Y-%m-%d %H:%M:%S")
    time_diff = datetime.now() - last_daily
    return time_diff >= timedelta(hours=24)

def update_daily_claim(user_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (now, user_id))
        conn.commit()

def get_all_users():
    # HIGH-01 FIX: Use context manager to prevent connection leaks during broadcast
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
        return [u[0] for u in cursor.fetchall()]

def get_active_task_count():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 1 AND completed_count < total_needed")
        return cursor.fetchone()[0]

def get_stats():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(points) FROM users")
        res = cursor.fetchone()
        # REM-02 FIX: SUM(points) returns NULL (Python None) if table is empty.
        # Return 0 instead to avoid 'None' showing in user-facing messages.
        total_users = res[0] if res[0] else 0
        total_points = res[1] if res[1] else 0
        return total_users, total_points

# --- TASK MANAGEMENT FUNCTIONS ---

def add_task(url, task_type, reward, total_needed):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO tasks (url, task_type, reward, total_needed, completed_count, status, created_at)
            VALUES (?, ?, ?, ?, 0, 1, ?)
        """, (url, task_type, reward, total_needed, created_at))
        conn.commit()

def get_available_tasks(user_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE status = 1 
            AND completed_count < total_needed
            AND id NOT IN (SELECT task_id FROM user_tasks WHERE user_id = ?)
        """, (user_id,))
        return cursor.fetchall()

def get_task_by_id(task_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return cursor.fetchone()

def submit_proof(user_id, task_id, screenshot_id, screenshot_unique_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        # 1. Check if user already submitted for this task
        cursor.execute("SELECT id FROM user_tasks WHERE user_id = ? AND task_id = ?", (user_id, task_id))
        if cursor.fetchone():
            return "ALREADY_SUBMITTED"
        
        # 2. Check if this exact photo was used before by ANYONE (Anti-Fraud)
        cursor.execute("SELECT id FROM user_tasks WHERE screenshot_unique_id = ?", (screenshot_unique_id,))
        if cursor.fetchone():
            return "DUPLICATE_PHOTO"
            
        submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO user_tasks (user_id, task_id, screenshot_id, screenshot_unique_id, submitted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, task_id, screenshot_id, screenshot_unique_id, submitted_at))
        sub_id = cursor.lastrowid
        conn.commit()
        return sub_id

def approve_submission(submission_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        
        # Get submission details
        cursor.execute("SELECT user_id, task_id FROM user_tasks WHERE id = ?", (submission_id,))
        res = cursor.fetchone()
        if not res:
            return False
            
        user_id, task_id = res
        
        # Get reward amount
        cursor.execute("SELECT reward FROM tasks WHERE id = ?", (task_id,))
        reward_res = cursor.fetchone()
        if not reward_res:
            return False
        reward = reward_res[0]
        
        # Update status to approved
        cursor.execute("UPDATE user_tasks SET status = 'approved' WHERE id = ?", (submission_id,))
        # Add points to user
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (reward, user_id))
        # Increment completed_count in tasks
        cursor.execute("UPDATE tasks SET completed_count = completed_count + 1 WHERE id = ?", (task_id,))
        
        conn.commit()
        return user_id, reward

def reject_submission(submission_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        
        # Get user_id for notification
        cursor.execute("SELECT user_id FROM user_tasks WHERE id = ?", (submission_id,))
        res = cursor.fetchone()
        if not res:
            return False
            
        user_id = res[0]
        
        # Update status to rejected
        cursor.execute("UPDATE user_tasks SET status = 'rejected' WHERE id = ?", (submission_id,))
        conn.commit()
        return user_id

def get_submission_by_id(submission_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_tasks WHERE id = ?", (submission_id,))
        return cursor.fetchone()

# --- WITHDRAWAL FUNCTIONS ---

def add_withdrawal_request(user_id, amount, method, details):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        # Check if user has enough points
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        if not res or res[0] < amount:
            return False
            
        # Deduct points immediately (pending)
        cursor.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (amount, user_id))
        
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO withdrawals (user_id, amount, method, details, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (user_id, amount, method, details, created_at))
        
        conn.commit()
        return True

def get_last_withdrawal_id(user_id):
    """Returns the most recently inserted withdrawal ID for a user."""
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM withdrawals WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        res = cursor.fetchone()
        return res[0] if res else None

def get_withdrawal_by_id(withdrawal_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
        return cursor.fetchone()

def approve_withdrawal(withdrawal_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        # REM-03 FIX: Fetch FIRST to verify record exists, THEN update.
        # Previous order was reversed: update ran even if ID was invalid.
        cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id = ?", (withdrawal_id,))
        res = cursor.fetchone()
        if not res:
            return None
        cursor.execute("UPDATE withdrawals SET status = 'approved' WHERE id = ?", (withdrawal_id,))
        conn.commit()
        return res

def reject_withdrawal(withdrawal_id):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        
        # Get details for refund
        cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id = ?", (withdrawal_id,))
        res = cursor.fetchone()
        if not res:
            return False
            
        user_id, amount = res
        
        # Update status to rejected
        cursor.execute("UPDATE withdrawals SET status = 'rejected' WHERE id = ?", (withdrawal_id,))
        # Refund points
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, user_id))
        
        conn.commit()
        return user_id, amount

def get_pending_counts():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_tasks WHERE status = 'pending'")
        task_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'")
        withd_count = cursor.fetchone()[0]
        return task_count, withd_count

def get_next_pending_task():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_tasks WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
        return cursor.fetchone()

def get_next_pending_withdrawal():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
        return cursor.fetchone()
