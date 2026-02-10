import psycopg2
from app.db import DB_HOST, DB_NAME, DB_USER, DB_PASS

def reset_db():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Drop all tables
    print("Dropping all tables...")
    cur.execute("DROP SCHEMA public CASCADE;")
    cur.execute("CREATE SCHEMA public;")
    
    conn.close()
    print("Database reset complete.")

if __name__ == "__main__":
    reset_db()
    from app import create_app
    from app.db import init_db
    
    app = create_app()
    with app.app_context():
        print("Initializing tables...")
        init_db()
