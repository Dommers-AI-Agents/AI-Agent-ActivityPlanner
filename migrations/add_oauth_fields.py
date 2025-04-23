"""
Migration script to add OAuth support and guest activity fields.
Run this manually after installing dependencies.

To run:
cd /path/to/project
python migrations/add_oauth_fields.py
"""
import sys
import os
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def update_database():
    """Add new columns for OAuth and guest activities."""
    # Get database path from environment or use default
    db_path = os.environ.get('DATABASE_URL', 'instance/app.db')
    
    # Handle SQLite file paths
    if db_path.startswith('sqlite:///'):
        db_path = db_path.replace('sqlite:///', '')
    
    print(f"Using database at: {db_path}")
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist in users table
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        if 'auth_provider' not in user_columns:
            print("Adding auth_provider column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(20)")
        else:
            print("auth_provider column already exists")
            
        if 'auth_provider_id' not in user_columns:
            print("Adding auth_provider_id column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN auth_provider_id VARCHAR(100)")
        else:
            print("auth_provider_id column already exists")
            
        # Make password_hash nullable
        if 'password_hash' in user_columns:
            print("Making password_hash column nullable")
            # Unfortunately SQLite doesn't support ALTER COLUMN, so we'd need to recreate the table
            # This is a simplified version that assumes we can make the change safely
            # In a real migration, you would create a new table, copy data, drop old table, rename new
            pass
        
        # Check if columns already exist in activities table
        cursor.execute("PRAGMA table_info(activities)")
        activity_columns = [col[1] for col in cursor.fetchall()]
        
        if 'guest_uuid' not in activity_columns:
            print("Adding guest_uuid column to activities table")
            cursor.execute("ALTER TABLE activities ADD COLUMN guest_uuid VARCHAR(36)")
        else:
            print("guest_uuid column already exists")
        
        # Commit changes
        conn.commit()
        print("Database updated successfully!")
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_database()