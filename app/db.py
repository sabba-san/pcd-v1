import psycopg2
import psycopg2.extras
from flask import g

# Database Configuration (Matches your docker-compose.yml)
DB_HOST = "flask_db"
DB_NAME = "flaskdb"
DB_USER = "user"
DB_PASS = "password"

def get_db():
    """Connects to the PostgreSQL database."""
    if 'db' not in g:
        try:
            g.db = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS
            )
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None
    return g.db

def close_db(e=None):
    """Closes the connection after the request ends."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Creates tables for ALL modules."""
    db = get_db()
    if db is None:
        print("Could not connect to database to initialize tables.")
        return

    cursor = db.cursor()
    
    # 1. Table for PROJECTS (Module 3)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            project_name TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Table for AI FEEDBACK (Module 4)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_feedback (
            id SERIAL PRIMARY KEY,
            user_message TEXT,
            ai_reply TEXT,
            feedback_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 3. Table for USERS (Login System)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    db.commit()
    cursor.close()
    print("Database tables initialized successfully.")
