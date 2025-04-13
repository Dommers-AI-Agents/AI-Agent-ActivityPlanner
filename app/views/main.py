"""
Main routes for the Group Activity Planner web interface.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, current_app
from app.models.database import Activity, Participant, Plan
from app.models.planner import ActivityPlanner
from app.services.sms_service import sms_service
from app.services.email_service import email_service
from app import db
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Landing page for the application."""
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard for managing activities."""
    # Get activities created by the current user
    activities = Activity.query.filter_by(creator_id=current_user.id).order_by(Activity.created_at.desc()).all()
    
    return render_template('dashboard.html', activities=activities)

@main_bp.route('/create-activity', methods=['GET', 'POST'])
@login_required
def create_activity():
    """Create a new activity and invite participants."""
    # When creating an activity, link it to the current user
    planner = ActivityPlanner()
    activity = planner.create_activity()
    activity.creator_id = current_user.id
    db.session.commit()
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

@main_bp.route('/activity/<activity_id>/resend-invitation/<participant_id>', methods=['POST'])
@login_required
def resend_invitation(activity_id, participant_id):
    """Resend invitation to a participant."""
    # Verify activity belongs to current user
    activity = Activity.query.get_or_404(activity_id)
    if activity.creator_id != current_user.id:
        flash("You don't have permission to do that.", "error")
        return redirect(url_for('main.dashboard'))
    
    # Get participant
    participant = Participant.query.get_or_404(participant_id)
    if participant.activity_id != activity_id:
        flash("Participant not found in this activity.", "error")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    # Resend invitation
    try:
        sms_service.send_welcome_message(participant.phone_number, activity_id, participant.id)
        if participant.email:
            email_service.send_welcome_email(
                participant.email,
                participant.name or "Participant",
                activity_id,
                participant.id
            )
        flash("Invitation resent successfully!", "success")
    except Exception as e:
        current_app.logger.error(f"Failed to resend invitation: {str(e)}")
        flash("Failed to resend invitation. Please try again.", "error")
    
    return redirect(url_for('main.activity_detail', activity_id=activity_id))

@main_bp.route('/activity/<activity_id>/resend-all-invitations', methods=['POST'])
@login_required
def resend_all_invitations(activity_id):
    """Resend invitations to all participants."""
    # Verify activity belongs to current user
    activity = Activity.query.get_or_404(activity_id)
    if activity.creator_id != current_user.id:
        flash("You don't have permission to do that.", "error")
        return redirect(url_for('main.dashboard'))
    
    # Get participants who haven't responded yet
    invited_participants = Participant.query.filter_by(
        activity_id=activity_id,
        status='invited'
    ).all()
    
    if not invited_participants:
        flash("No pending invitations to resend.", "info")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    # Count successful resends
    success_count = 0
    
    # Resend invitations
    for participant in invited_participants:
        try:
            sms_service.send_welcome_message(participant.phone_number, activity_id, participant.id)
            if participant.email:
                email_service.send_welcome_email(
                    participant.email,
                    participant.name or "Participant",
                    activity_id,
                    participant.id
                )
            success_count += 1
        except Exception as e:
            current_app.logger.error(f"Failed to resend invitation to {participant.phone_number}: {str(e)}")
    
    if success_count > 0:
        flash(f"Successfully resent {success_count} invitation(s)!", "success")
    else:
        flash("Failed to resend invitations. Please try again.", "error")
    
    return redirect(url_for('main.activity_detail', activity_id=activity_id))

@main_bp.route('/activity/<activity_id>/reset-progress/<participant_id>', methods=['POST'])
@login_required
def reset_participant_progress(activity_id, participant_id):
    """Reset a participant's progress to restart the questionnaire."""
    # Verify activity belongs to current user
    activity = Activity.query.get_or_404(activity_id)
    if activity.creator_id != current_user.id:
        flash("You don't have permission to do that.", "error")
        return redirect(url_for('main.dashboard'))
    
    # Get participant
    participant = Participant.query.get_or_404(participant_id)
    if participant.activity_id != activity_id:
        flash("Participant not found in this activity.", "error")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    try:
        # Reset the participant's progress using the helper function
        _reset_participant_preferences(activity_id, participant_id)
        
        # Resend invitation
        sms_service.send_welcome_message(participant.phone_number, activity_id, participant.id)
        if participant.email:
            email_service.send_welcome_email(
                participant.email,
                participant.name or "Participant",
                activity_id,
                participant.id
            )
        
        flash(f"Progress reset for {participant.name or 'participant'}. New invitation sent.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to reset participant progress: {str(e)}")
        flash("Failed to reset participant progress. Please try again.", "error")
    
    return redirect(url_for('main.activity_detail', activity_id=activity_id))

@main_bp.route('/activity/<activity_id>/self-reset', methods=['POST'])
def self_reset_progress(activity_id):
    """Allow participants to reset their own progress to restart the questionnaire."""
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
    
    try:
        # Reset the participant's preferences
        _reset_participant_preferences(activity_id, participant_id)
        flash("Your preferences have been reset. You can now restart the questionnaire with the latest questions.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to reset participant progress: {str(e)}")
        flash("Failed to reset your progress. Please try again.", "error")
    
    return redirect(url_for('main.activity_questions', activity_id=activity_id))

def _reset_participant_preferences(activity_id, participant_id):
    """Helper function to reset a participant's preferences."""
    # Get participant
    participant = Participant.query.get(participant_id)
    if not participant:
        raise ValueError(f"Participant with ID {participant_id} not found")
    
    # Delete all preferences except contact info
    contact_preferences = {}
    contact_preferences_query = Preference.query.filter_by(
        activity_id=activity_id,
        participant_id=participant_id,
        category='contact'
    ).all()
    
    # Save contact preferences
    for pref in contact_preferences_query:
        contact_preferences[pref.key] = pref.value
    
    # Delete all preferences
    Preference.query.filter_by(
        activity_id=activity_id,
        participant_id=participant_id
    ).delete()
    
    db.session.commit()
    
    # Restore contact preferences
    for key, value in contact_preferences.items():
        preference = Preference(
            activity_id=activity_id,
            participant_id=participant_id,
            category='contact',
            key=key,
            value=value
        )
        db.session.add(preference)
    
    # Reset participant status
    participant.status = 'invited'
    db.session.commit()
    
    return participant

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
    
    # Force reload participant data to ensure we're using the latest data and questions
    db.session.refresh(participant)
    
    # Initialize planner and get next questions
    planner = ActivityPlanner(activity_id)
    
    # For debugging - check if we're getting the new questions format
    current_app.logger.info(f"Getting questions batch for participant {participant_id} with status {participant.status}")
    
    # Get the questions
    questions = planner.generate_questions_batch(participant_id)
    
    # Log the first question's information for debugging
    if questions and len(questions) > 0:
        current_app.logger.info(f"First question: {questions[0]['question']}")
        
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
        current_app.logger.error(f"No participant ID in session for activity {activity_id}")
        return jsonify({"error": "Unauthorized - No participant in session"}), 401
    
    participant = Participant.query.get(participant_id)
    if not participant or participant.activity_id != activity_id:
        current_app.logger.error(f"Invalid participant {participant_id} for activity {activity_id}")
        return jsonify({"error": "Unauthorized - Invalid participant"}), 401
    
    # Log participant status
    current_app.logger.info(f"Processing answers for participant {participant_id} (status: {participant.status})")
    
    # Process the submitted answers
    answers = request.json.get('answers', {})
    current_app.logger.info(f"Received answers: {answers}")
    
    if not answers:
        current_app.logger.warning(f"No answers submitted for participant {participant_id}")
        return jsonify({"error": "No answers provided"}), 400
    
    # Save answers as preferences
    planner = ActivityPlanner(activity_id)
    for question_id, answer in answers.items():
        # Determine category based on question ID or batch
        if question_id in ['email', 'name', 'allow_group_text']:
            category = 'contact'
        elif question_id in ['group_size', 'has_children', 'has_seniors', 'social_level']:
            category = 'group'
        elif question_id in ['preferred_day', 'preferred_time', 'duration']:
            category = 'timing'
        elif question_id in ['activity_type', 'physical_exertion', 'budget_range', 'learning_preference']:
            category = 'activity'
        elif question_id in ['meals_included']:
            category = 'meals'
        elif question_id in ['dietary_restrictions', 'accessibility_needs', 'additional_info', 'direct_input']:
            category = 'requirements'
        else:
            category = 'other'
            current_app.logger.info(f"Question {question_id} mapped to 'other' category")
        
        # Log the preference being saved
        current_app.logger.info(f"Saving preference: {category}.{question_id} = {answer}")
        
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
        current_app.logger.info(f"Updated participant {participant_id} status to 'active'")
    
    # Force database refresh before getting next questions
    db.session.refresh(participant)
    
    # Get next batch of questions
    current_app.logger.info(f"Getting next question batch for participant {participant_id}")
    next_questions = planner.generate_questions_batch(participant_id)
    
    # Log the next questions or completion
    if next_questions is None:
        current_app.logger.info(f"No more questions for participant {participant_id}")
        participant.status = 'complete'
        db.session.commit()
        current_app.logger.info(f"Updated participant {participant_id} status to 'complete'")
    else:
        current_app.logger.info(f"Next batch has {len(next_questions)} questions")
        current_app.logger.info(f"First question: {next_questions[0]['question'] if next_questions else 'None'}")
    
    # Prepare response
    response_data = {
        "success": True,
        "next_questions": next_questions,
        "complete": next_questions is None
    }
    current_app.logger.info(f"Returning response: {response_data}")
    
    return jsonify(response_data)

@main_bp.route('/activity/<activity_id>/generate-plan')
def generate_plan(activity_id):
    """Generate an activity plan."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Check if at least one participant has completed their preferences
    stats = activity.get_response_stats()
    if stats['completed'] == 0:
        flash("Unable to generate a plan. At least one participant must complete all preference questions.", "error")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
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

@main_bp.route('/activity/<activity_id>/delete', methods=['POST'])
@login_required
def delete_activity(activity_id):
    """Delete an activity."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Verify activity belongs to current user
    if activity.creator_id != current_user.id:
        flash("You don't have permission to delete this activity.", "error")
        return redirect(url_for('main.dashboard'))
    
    try:
        # Delete associated participants, plans, and preferences
        Plan.query.filter_by(activity_id=activity_id).delete()
        
        # Delete all participants of the activity
        participants = Participant.query.filter_by(activity_id=activity_id).all()
        for participant in participants:
            # Delete preferences for each participant
            db.session.execute(
                'DELETE FROM preferences WHERE participant_id = :participant_id',
                {'participant_id': participant.id}
            )
        
        Participant.query.filter_by(activity_id=activity_id).delete()
        
        # Delete the activity
        db.session.delete(activity)
        db.session.commit()
        
        flash("Activity deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete activity: {str(e)}")
        flash("Failed to delete activity. Please try again.", "error")
    
    return redirect(url_for('main.dashboard'))
