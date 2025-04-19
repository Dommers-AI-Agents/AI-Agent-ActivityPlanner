"""
Temporary script to create the AI suggestions and plan approvals tables.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Create ai_suggestions table
    db.session.execute(text('''
    CREATE TABLE IF NOT EXISTS ai_suggestions (
        id VARCHAR(36) PRIMARY KEY,
        plan_id VARCHAR(36) NOT NULL,
        activity_id VARCHAR(36) NOT NULL,
        summary TEXT NOT NULL,
        changes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (plan_id) REFERENCES plans (id),
        FOREIGN KEY (activity_id) REFERENCES activities (id)
    )
    '''))
    
    # Create plan_approvals table
    db.session.execute(text('''
    CREATE TABLE IF NOT EXISTS plan_approvals (
        id VARCHAR(36) PRIMARY KEY,
        plan_id VARCHAR(36) NOT NULL,
        participant_id VARCHAR(36) NOT NULL,
        approved BOOLEAN DEFAULT FALSE,
        feedback TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (plan_id) REFERENCES plans (id),
        FOREIGN KEY (participant_id) REFERENCES participants (id)
    )
    '''))
    
    db.session.commit()
    print("Tables created successfully!")