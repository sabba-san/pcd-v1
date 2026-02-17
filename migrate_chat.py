from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Starting ChatHistory migration...")
    
    # Check if columns exist before adding
    try:
        with db.engine.connect() as conn:
            # Add session_id
            try:
                conn.execute(text("ALTER TABLE chat_history ADD COLUMN session_id VARCHAR(100)"))
                print("Added column: session_id")
            except Exception as e:
                print(f"Skipping session_id (might exist): {e}")

            # Add title
            try:
                conn.execute(text("ALTER TABLE chat_history ADD COLUMN title VARCHAR(200)"))
                print("Added column: title")
            except Exception as e:
                print(f"Skipping title (might exist): {e}")
                
            # Set default values for existing rows if any
            # We'll generate a default session ID for old messages if they exist
            conn.execute(text("UPDATE chat_history SET session_id = 'legacy_session' WHERE session_id IS NULL"))
            conn.execute(text("UPDATE chat_history SET title = 'Legacy Chat' WHERE title IS NULL"))
            
            conn.commit()
            print("Migration completed successfully.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
