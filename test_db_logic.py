import sqlite3
import os
import database as db

# Setup a test database
TEST_DB = "test_bot.db"
db.DB_NAME = TEST_DB

def setup_test_data():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    db.init_db()
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    
    # Add some tasks
    # (url, task_type, reward, total_needed, completed_count, status, created_at)
    cursor.execute("INSERT INTO tasks (url, task_type, reward, total_needed, completed_count, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("url1", "Follow", 10, 5, 0, 1, "2024-01-01")) # Active, not finished
    cursor.execute("INSERT INTO tasks (url, task_type, reward, total_needed, completed_count, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("url2", "Like", 20, 5, 5, 1, "2024-01-01"))   # Active, but finished
    cursor.execute("INSERT INTO tasks (url, task_type, reward, total_needed, completed_count, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("url3", "Comment", 30, 5, 0, 0, "2024-01-01")) # Inactive
    cursor.execute("INSERT INTO tasks (url, task_type, reward, total_needed, completed_count, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("url4", "Share", 40, 5, 0, 1, "2024-01-01")) # Active, user will have submission
    
    # Add a submission for User 123 on Task 4
    cursor.execute("INSERT INTO user_tasks (user_id, task_id, screenshot_id, status, submitted_at) VALUES (?, ?, ?, ?, ?)",
                   (123, 4, "photo1", "pending", "2024-01-01"))
    
    conn.commit()
    conn.close()

def run_test():
    setup_test_data()
    
    print("Testing for User 123:")
    tasks = db.get_available_tasks(123)
    print(f"Found {len(tasks)} tasks.")
    for t in tasks:
        print(f"Task ID: {t[0]}, Type: {t[2]}, Status: {t[6]}, Count: {t[5]}/{t[4]}")
        
    print("\nTesting for User 456 (New user):")
    tasks = db.get_available_tasks(456)
    print(f"Found {len(tasks)} tasks.")
    for t in tasks:
        print(f"Task ID: {t[0]}, Type: {t[2]}, Status: {t[6]}, Count: {t[5]}/{t[4]}")

    # Expected for 123: Only Task 1. (Task 2 finished, Task 3 inactive, Task 4 already submitted)
    # Expected for 456: Task 1 and Task 4. (Task 2 finished, Task 3 inactive)

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

if __name__ == "__main__":
    run_test()
