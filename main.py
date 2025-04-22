"""
Main routes for the Group Activity Planner web interface.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, current_app
from app.models.database import Activity, Participant, Plan
from app.models.planner import ActivityPlanner
from app.services.sms_service import sms_service
from app.services.email_service import email_service
from app import db
import os
from dotenv import load_dotenv

# Load environment variables
print("Loading environment variables from .env file...")
load_dotenv(verbose=True)
print(f"ANTHROPIC_API_KEY available: {'Yes' if os.environ.get('ANTHROPIC_API_KEY') else 'No'}")
print(f"CLAUDE_MODEL available: {'Yes' if os.environ.get('CLAUDE_MODEL') else 'No'}")

main_bp = Blueprint('main', __name__)

from app import create_app

# Create the Flask application instance
app = create_app()

def get_app():
    """Return the application instance."""
    return app

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))

    cert_path = os.path.join(os.path.dirname(__file__), 'ssl/cloudflare.pem')
    key_path = os.path.join(os.path.dirname(__file__), 'ssl/cloudflare-key.pem')
        
    # Run the application
    app.run(
        host='0.0.0.0', port=port,
        ssl_context=(cert_path, key_path)
        )

@main_bp.route('/')
def index():
    """Landing page for the application."""
    return render_template('index.html')

@main_bp.route('/create-activity', methods=['GET', 'POST'])
def create_activity():
    """Create a new activity and invite participants."""
    if request.method == 'POST':
        # Process form data
        organizer_name = request.form.get('organizer_name')
        organizer_phone = request.form.get('organizer_phone')
        organizer_email = request.form.get('organizer_email')
        
        # Create new activity
        planner = ActivityPlanner()
        activity = planner.create_activity()
        
        # Add organizer as first participant
        organizer = planner.add_participant(
            phone_number=organizer_phone,
            email=organizer_email,
            name=organizer_name
        )
        
        # Save organizer details as preferences
        planner.save_preference(organizer.id, 'contact', 'name', organizer_name)
        planner.save_preference(organizer.id, 'contact', 'email', organizer_email)
        planner.save_preference(organizer.id, 'contact', 'phone', organizer_phone)
        
        # Process additional participants
        participant_phones = request.form.getlist('participant_phone')
        participant_emails = request.form.getlist('participant_email')
        participant_names = request.form.getlist('participant_name')
        
        # Add each participant and send invitation
        for i in range(len(participant_phones)):
            if participant_phones[i]:
                phone = participant_phones[i]
                email = participant_emails[i] if i < len(participant_emails) else None
                name = participant_names[i] if i < len(participant_names) else None
                
                # Add participant to the activity
                participant = planner.add_participant(
                    phone_number=phone,
                    email=email,
                    name=name
                )
                
                # Save basic contact info
                if name:
                    planner.save_preference(participant.id, 'contact', 'name', name)
                if email:
                    planner.save_preference(participant.id, 'contact', 'email', email)
                
                # Send SMS invitation
                try:
                    sms_service.send_welcome_message(phone, activity.id, participant.id)
                except Exception as e:
                    current_app.logger.error(f"Failed to send SMS to {phone}: {str(e)}")
                
                # Send email invitation if available
                if email:
                    try:
                        email_service.send_welcome_email(
                            email,
                            name or "Participant",
                            activity.id,
                            participant.id
                        )
                    except Exception as e:
                        current_app.logger.error(f"Failed to send email to {email}: {str(e)}")
        
        # Redirect to the activity page
        return redirect(url_for('main.activity_detail', activity_id=activity.id))
    
    # Show the create activity form
    return render_template('create_activity.html')

@main_bp.route('/activity/<activity_id>')
def activity_detail(activity_id):
    """Activity detail page."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Check if this is a participant accessing via their link
    participant_id = request.args.get('participant')
    participant = None
    
    if participant_id:
        participant = Participant.query.get(participant_id)
        
        # Store the participant ID in session for this activity
        if participant and participant.activity_id == activity_id:
            session[f'activity_{activity_id}_participant'] = participant_id
    
    # Otherwise get participant from session
    elif f'activity_{activity_id}_participant' in session:
        participant_id = session[f'activity_{activity_id}_participant']
        participant = Participant.query.get(participant_id)
    
    # Check if there's a plan
    plan = Plan.query.filter_by(activity_id=activity_id).order_by(Plan.created_at.desc()).first()
    
    return render_template(
        'activity_detail.html',
        activity=activity,
        participant=participant,
        plan=plan
    )

@main_bp.route('/activity/<activity_id>/questions')
def activity_questions(activity_id):
    """Page for answering questions about preferences."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Get the participant from session
    participant_id = session.get(f'activity_{activity_id}_participant')
    if not participant_id:
        flash("Please access this page through your invitation link.", "error")
        return redirect(url_for('main.index'))
    
    participant = Participant.query.get(participant_id)
    if not participant or participant.activity_id != activity_id:
        flash("Invalid participant access.", "error")
        return redirect(url_for('main.index'))
    
    # Initialize planner and get next questions
    planner = ActivityPlanner(activity_id)
    questions = planner.generate_questions_batch(participant_id)
    
    # Check if we've answered all questions
    all_complete = questions is None
    
    return render_template(
        'questions.html',
        activity=activity,
        participant=participant,
        questions=questions,
        all_complete=all_complete
    )

@main_bp.route('/activity/<activity_id>/submit-answers', methods=['POST'])
def submit_answers(activity_id):
    """Submit answers to questions."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Get the participant from session
    participant_id = session.get(f'activity_{activity_id}_participant')
    if not participant_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    participant = Participant.query.get(participant_id)
    if not participant or participant.activity_id != activity_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Process the submitted answers
    answers = request.json.get('answers', {})
    
    # Save answers as preferences
    planner = ActivityPlanner(activity_id)
    for question_id, answer in answers.items():
        # Determine category based on question ID or batch
        if question_id in ['email', 'name', 'allow_group_text']:
            category = 'contact'
        elif question_id in ['group_size', 'has_children', 'has_seniors']:
            category = 'group'
        elif question_id in ['preferred_day', 'preferred_time', 'duration']:
            category = 'timing'
        elif question_id in ['activity_type', 'walking_preference', 'budget_range']:
            category = 'activity'
        elif question_id in ['dietary_restrictions', 'accessibility_needs', 'additional_info']:
            category = 'requirements'
        else:
            category = 'other'
        
        # Save the preference
        planner.save_preference(participant_id, category, question_id, answer)
        
        # Update participant record for special fields
        if question_id == 'email':
            participant.email = answer
        elif question_id == 'name':
            participant.name = answer
        elif question_id == 'allow_group_text':
            participant.allow_group_text = answer
    
    # Update participant status
    if answers:
        participant.status = 'active'
        db.session.commit()
    
    # Get next batch of questions
    next_questions = planner.generate_questions_batch(participant_id)
    
    # Update status to complete if no more questions
    if next_questions is None:
        participant.status = 'complete'
        db.session.commit()
    
    return jsonify({
        "success": True,
        "next_questions": next_questions,
        "complete": next_questions is None
    })

@main_bp.route('/activity/<activity_id>/generate-plan')
def generate_plan(activity_id):
    """Generate an activity plan."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Initialize planner and generate plan
    planner = ActivityPlanner(activity_id)
    plan = planner.generate_plan()
    
    # Notify all participants
    for participant in activity.participants:
        # Skip participants without email
        if not participant.email:
            continue
        
        try:
            email_service.send_plan_email(
                participant.email,
                participant.name or "Participant",
                activity_id,
                plan.to_dict()
            )
        except Exception as e:
            current_app.logger.error(f"Failed to send plan email to {participant.email}: {str(e)}")
        
        # Send SMS notification if they opted in
        if participant.allow_group_text and participant.phone_number:
            try:
                sms_service.send_plan_notification(
                    participant.phone_number,
                    activity_id,
                    plan.to_dict()
                )
            except Exception as e:
                current_app.logger.error(f"Failed to send plan SMS to {participant.phone_number}: {str(e)}")
    
    # Redirect to plan page
    return redirect(url_for('main.view_plan', activity_id=activity_id))

@main_bp.route('/activity/<activity_id>/plan')
def view_plan(activity_id):
    """View the activity plan."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Get the most recent plan
    plan = Plan.query.filter_by(activity_id=activity_id).order_by(Plan.created_at.desc()).first()
    if not plan:
        flash("No plan has been generated yet.", "warning")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    # Get the participant from session
    participant_id = session.get(f'activity_{activity_id}_participant')
    participant = None
    if participant_id:
        participant = Participant.query.get(participant_id)
    
    return render_template(
        'plan.html',
        activity=activity,
        plan=plan,
        participant=participant
    )

@main_bp.route('/activity/<activity_id>/feedback', methods=['GET', 'POST'])
def submit_feedback(activity_id):
    """Submit feedback on the plan."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Get the most recent plan
    plan = Plan.query.filter_by(activity_id=activity_id).order_by(Plan.created_at.desc()).first()
    if not plan:
        flash("No plan has been generated yet.", "warning")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    # Get the participant from session
    participant_id = session.get(f'activity_{activity_id}_participant')
    if not participant_id:
        flash("Please access this page through your invitation link.", "error")
        return redirect(url_for('main.index'))
    
    participant = Participant.query.get(participant_id)
    if not participant or participant.activity_id != activity_id:
        flash("Invalid participant access.", "error")
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Process feedback
        feedback = request.form.get('feedback')
        
        if feedback:
            # Initialize planner and revise plan
            planner = ActivityPlanner(activity_id)
            revised_plan = planner.revise_plan(plan.id, feedback)
            
            # Save the feedback as a preference
            planner.save_preference(participant_id, 'feedback', 'plan_feedback', feedback)
            
            flash("Thank you for your feedback! The plan has been updated.", "success")
            
            # Notify all participants about the update
            for p in activity.participants:
                # Skip participants without email
                if not p.email:
                    continue
                
                try:
                    email_service.send_group_notification(
                        [p.email],
                        "Group Activity Plan Updated",
                        f"The plan has been updated based on feedback. Please check the latest version.",
                        activity_id
                    )
                except Exception as e:
                    current_app.logger.error(f"Failed to send update email to {p.email}: {str(e)}")
                
                # Send SMS notification if they opted in
                if p.allow_group_text and p.phone_number:
                    try:
                        sms_service.send_notification(
                            p.phone_number,
                            "The group activity plan has been updated based on feedback. Check your email for details.",
                            activity_id
                        )
                    except Exception as e:
                        current_app.logger.error(f"Failed to send update SMS to {p.phone_number}: {str(e)}")
            
            return redirect(url_for('main.view_plan', activity_id=activity_id))
    
    return render_template(
        'feedback.html',
        activity=activity,
        plan=plan,
        participant=participant
    )

@main_bp.route('/activity/<activity_id>/finalize')
def finalize_plan(activity_id):
    """Finalize the activity plan."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Get the most recent plan
    plan = Plan.query.filter_by(activity_id=activity_id).order_by(Plan.created_at.desc()).first()
    if not plan:
        flash("No plan has been generated yet.", "warning")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    # Update plan status
    plan.status = 'final'
    activity.status = 'finalized'
    db.session.commit()
    
    # Notify all participants
    for participant in activity.participants:
        # Skip participants without email
        if not participant.email:
            continue
        
        try:
            email_service.send_plan_email(
                participant.email,
                participant.name or "Participant",
                activity_id,
                plan.to_dict(),
                is_final=True
            )
        except Exception as e:
            current_app.logger.error(f"Failed to send final plan email to {participant.email}: {str(e)}")
        
        # Send SMS notification if they opted in
        if participant.allow_group_text and participant.phone_number:
            try:
                sms_service.send_notification(
                    participant.phone_number,
                    "The group activity plan has been finalized! Check your email for all the details.",
                    activity_id
                )
            except Exception as e:
                current_app.logger.error(f"Failed to send final plan SMS to {participant.phone_number}: {str(e)}")
    
    flash("The plan has been finalized and all participants have been notified.", "success")
    return redirect(url_for('main.view_plan', activity_id=activity_id))
