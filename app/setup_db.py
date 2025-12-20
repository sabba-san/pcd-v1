import sqlite3

def create_database():
    # This creates (or connects to) a file named 'app.db'
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()

    # Create the 'defects' table with a STATUS column
    # This 'status' column is what you need for the "Lock" feature
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

    # Add dummy data so the table isn't empty
    cursor.execute('''
        INSERT INTO defects (project_name, unit_no, description, status)
        VALUES ('ASMARINDA12', 'A-85', 'Structural Wall Crack in Master Bedroom', 'draft')
    ''')

    conn.commit()
    conn.close()
    print("Success! Database 'app.db' created.")

if __name__ == "__main__":
    create_database()