"""
Repair script to check and fix feedback preferences in the database.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app, db
from app.models.database import Preference, Activity, Participant, Plan
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Running feedback repair script...")
    
    # Get all activities with plans
    activities_with_plans = db.session.query(Activity).join(
        Plan, Activity.id == Plan.activity_id
    ).all()
    
    print(f"Found {len(activities_with_plans)} activities with plans")
    
    # For each activity with a plan
    for activity in activities_with_plans:
        print(f"\nChecking Activity {activity.id}: {activity.title or 'Untitled'}")
        
        # Get all participants for this activity
        participants = Participant.query.filter_by(activity_id=activity.id).all()
        print(f"  {len(participants)} participants")
        
        # Get all plans for this activity
        plans = Plan.query.filter_by(activity_id=activity.id).all()
        print(f"  {len(plans)} plans")
        
        # Get feedback preferences for this activity
        feedback_prefs = Preference.query.filter_by(
            activity_id=activity.id,
            category='feedback',
            key='plan_feedback'
        ).all()
        print(f"  {len(feedback_prefs)} feedback preferences")
        
        if len(feedback_prefs) == 0:
            print("  No feedback preferences found. Checking for mismatched activity IDs...")
            
            # Check if there are feedback preferences for any participants
            for participant in participants:
                # Check all preferences
                participant_prefs = Preference.query.filter_by(
                    participant_id=participant.id,
                    category='feedback',
                    key='plan_feedback'
                ).all()
                
                if len(participant_prefs) > 0:
                    print(f"  Found {len(participant_prefs)} mismatched feedback preferences for participant {participant.id}")
                    
                    # Fix the preferences
                    for pref in participant_prefs:
                        old_activity_id = pref.activity_id
                        pref.activity_id = activity.id
                        print(f"    Updating preference {pref.id} activity_id from {old_activity_id} to {activity.id}")
            
            # Commit changes
            db.session.commit()
            print("  Changes committed to database")
            
            # Verify fix
            fixed_prefs = Preference.query.filter_by(
                activity_id=activity.id,
                category='feedback',
                key='plan_feedback'
            ).all()
            print(f"  After fixing: {len(fixed_prefs)} feedback preferences")
    
    print("\nRepair script completed.")