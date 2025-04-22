"""
Migration script to remove username column from the users table.
"""
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def migrate():
    """
    Remove the username column from the users table and update existing users
    to use their email as identifier.
    """
    print("Starting migration to remove username column...")
    
    # For SQLite, we need to check table structure differently
    result = db.session.execute(
        text("PRAGMA table_info(users)")
    ).fetchall()
    
    # Check if username column exists
    column_exists = False
    for column in result:
        if column[1] == 'username':  # column[1] is the column name
            column_exists = True
            break
    
    if column_exists:
        print("Username column exists, proceeding with migration.")
    else:
        print("Username column doesn't exist, no migration needed.")
        return
    
    # First, make sure all users have email set to a valid value
    print("Verifying all users have valid emails...")
    no_email_count = db.session.execute(
        text("SELECT COUNT(*) FROM users WHERE email IS NULL OR email = ''")
    ).scalar()
    
    if no_email_count > 0:
        print(f"WARNING: {no_email_count} users do not have a valid email. Migration aborted.")
        return
    
    # In SQLite, we can't just drop a column, we need to recreate the table
    # Create a new table without the username column
    print("Recreating users table without username column...")
    
    # Get all current users first
    users = db.session.execute(
        text("SELECT id, email, password_hash, name, created_at FROM users")
    ).fetchall()
    
    # Create a temporary table
    db.session.execute(text("""
        CREATE TABLE users_new (
            id VARCHAR(36) PRIMARY KEY, 
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(128) NOT NULL,
            name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Copy the data
    for user in users:
        db.session.execute(text("""
            INSERT INTO users_new (id, email, password_hash, name, created_at)
            VALUES (:id, :email, :password_hash, :name, :created_at)
        """), {
            'id': user[0],
            'email': user[1],
            'password_hash': user[2],
            'name': user[3],
            'created_at': user[4]
        })
    
    # Drop the old table and rename the new one
    db.session.execute(text("DROP TABLE users"))
    db.session.execute(text("ALTER TABLE users_new RENAME TO users"))
    
    # Commit the changes
    db.session.commit()
    print("Migration complete!")

if __name__ == "__main__":
    # Create app context
    app = create_app()
    with app.app_context():
        migrate()