import sqlite3
import os

# 1. Calculate the exact path to the database (Same as your routes.py)
# This points to /home/abbas/development/pcd/app.db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'app.db')

print(f"Checking database at: {DATABASE_PATH}")

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # 2. Create the table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            unit_no TEXT,
            description TEXT,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Add a test item so you know it worked
    cursor.execute('''
        INSERT INTO defects (project_name, unit_no, description, status)
        VALUES ('TEST PROJECT', 'A-00', 'Database Connection Verification', 'draft')
    ''')

    conn.commit()
    conn.close()
    print("Success! Table 'defects' created.")

if __name__ == '__main__':
    init_db()