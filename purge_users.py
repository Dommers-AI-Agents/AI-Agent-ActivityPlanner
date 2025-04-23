#!/usr/bin/env python3
"""
Script to remove all users except for wesley@aibuilder.org
"""
import os
import sys
from dotenv import load_dotenv

# Add current directory to path so we can import main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv(verbose=True)

# Now import from main which is in the path
from main import app  # This is the Flask app defined in main.py
from app.models.database import User, db

def run_migration():
    """Execute the migration to remove all users except wesley@aibuilder.org"""
    print("Starting purge: remove all users except wesley@aibuilder.org")
    
    # Count total users before deletion
    total_users = User.query.count()
    print(f"Total users before purge: {total_users}")
    
    # Find the user to keep
    wesley = User.query.filter_by(email='wesley@aibuilder.org').first()
    if not wesley:
        print("WARNING: User wesley@aibuilder.org not found in database!")
        print("No users will be deleted.")
        return
    
    print(f"Keeping user ID {wesley.id}: {wesley.name} ({wesley.email})")
    
    # Find users to delete
    users_to_delete = User.query.filter(User.id != wesley.id).all()
    print(f"Found {len(users_to_delete)} users to delete")
    
    # Confirm before deletion
    if len(users_to_delete) == 0:
        print("No users to delete. Exiting.")
        return
        
    confirmation = input(f"Are you sure you want to delete {len(users_to_delete)} users? (yes/no): ")
    if confirmation.lower() != 'yes':
        print("Purge cancelled.")
        return
    
    # Delete users
    for user in users_to_delete:
        print(f"Deleting user ID {user.id}: {user.name} ({user.email})")
        db.session.delete(user)
    
    # Commit changes
    db.session.commit()
    print("Purge completed successfully.")
    
    # Verify remaining users
    remaining = User.query.all()
    print(f"\nRemaining users ({len(remaining)}):")
    for user in remaining:
        print(f'ID {user.id}: {user.name} ({user.email})')

if __name__ == '__main__':
    with app.app_context():
        run_migration()