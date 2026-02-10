import psycopg2
import psycopg2.extras
import click
from flask import g, current_app
from flask.cli import with_appcontext

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
    
    # 0. Table for USERS (Login System) - Must be first for Foreign Keys
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            project_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 1. Table for PROJECTS (Module 3)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            project_name TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Table for SCANS (Module 3 - Visualizer)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            model_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 3. Table for DEFECTS (Module 2)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defects (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            scan_id INTEGER REFERENCES scans(id),
            x FLOAT NOT NULL,
            y FLOAT NOT NULL,
            z FLOAT NOT NULL,
            element VARCHAR(255),
            location VARCHAR(100),
            defect_type VARCHAR(50) DEFAULT 'Unknown',
            severity VARCHAR(20) DEFAULT 'Medium',
            priority VARCHAR(20) DEFAULT 'Medium',
            description TEXT,
            status VARCHAR(50) DEFAULT 'Reported',
            image_path VARCHAR(500),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 4. Table for ACTIVITY LOGS (Module 3)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id SERIAL PRIMARY KEY,
            defect_id INTEGER REFERENCES defects(id),
            scan_id INTEGER REFERENCES scans(id),
            action VARCHAR(255) NOT NULL,
            old_value VARCHAR(255),
            new_value VARCHAR(255),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 5. Table for AI FEEDBACK (Module 1)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_feedback (
            id SERIAL PRIMARY KEY,
            user_message TEXT,
            ai_reply TEXT,
            feedback_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)



    db.commit()
    cursor.close()
    print("Database tables initialized successfully.")

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
