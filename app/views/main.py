"""
Main routes for the Group Activity Planner web interface.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, current_app
from app.models.database import Activity, Participant, Plan, Preference, AISuggestion, PlanApproval
from app.models.planner import ActivityPlanner
from app.services.sms_service import sms_service
from app.services.email_service import email_service
from app.services.claude_service import claude_service
from sqlalchemy import text
from app import db
from flask_login import login_required, current_user
from datetime import datetime

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
    if request.method == 'POST':
        # Process form data
        activity_name = request.form.get('activity_name')
        organizer_name = request.form.get('organizer_name')
        organizer_phone = request.form.get('organizer_phone')
        organizer_email = request.form.get('organizer_email')
        
        # Get date and time window information
        activity_date = request.form.get('activity_date')
        activity_time_window = request.form.get('activity_time_window')
        activity_start_time = request.form.get('activity_start_time')
        activity_location = request.form.get('activity_location')
        
        # Handle custom time window if selected
        if activity_time_window == 'Custom':
            time_start = request.form.get('activity_time_start')
            time_end = request.form.get('activity_time_end')
            if time_start and time_end:
                activity_time_window = f"Custom ({time_start} to {time_end})"

        # Check for AI conversation data
        ai_conversation_summary = request.form.get('ai_conversation_summary')
        activity_description = request.form.get('activity_description')
        activity_type = request.form.get('activity_type')
        special_considerations = request.form.get('special_considerations')
        
        # Create new activity
        planner = ActivityPlanner()
        activity = planner.create_activity()
        activity.title = activity_name
        activity.creator_id = current_user.id
        
        # Save the detailed activity description from the AI conversation
        if activity_description:
            activity.description = activity_description
        elif activity_type:
            activity.description = ai_conversation_summary
        
        # Save date and time window
        if activity_date:
            try:
                activity.proposed_date = datetime.strptime(activity_date, '%Y-%m-%d').date()
            except Exception as e:
                current_app.logger.error(f"Error parsing date {activity_date}: {str(e)}")
        
        if activity_time_window:
            activity.time_window = activity_time_window
            
        if activity_start_time:
            activity.start_time = activity_start_time
            
        if activity_location:
            activity.location_address = activity_location
        
        # Save the date and time as preferences too, for easier querying
        planner.save_preference(None, 'timing', 'proposed_date', activity_date)
        planner.save_preference(None, 'timing', 'time_window', activity_time_window)
        planner.save_preference(None, 'timing', 'start_time', activity_start_time)
        planner.save_preference(None, 'location', 'address', activity_location)
            
        db.session.commit()
        
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
                    current_app.logger.info(f"Attempting to send SMS to {phone} for activity {activity.id}")
                    result = sms_service.send_welcome_message(phone, activity.id, participant.id)
                    current_app.logger.info(f"SMS sent successfully to {phone}: {result}")
                except Exception as e:
                    current_app.logger.error(f"Failed to send SMS to {phone}: {str(e)}", exc_info=True)
                    # Add a flash message to notify about the SMS failure
                    flash(f"Note: SMS invitation to {phone} couldn't be sent. Participants can still be invited manually.", "warning")
                
                # Send email invitation if available
                if email:
                    try:
                        current_app.logger.info(f"Attempting to send email to {email} for activity {activity.id}")
                        email_service.send_welcome_email(
                            email,
                            name or "Participant",
                            activity.id,
                            participant.id
                        )
                        current_app.logger.info(f"Email sent successfully to {email}")
                    except Exception as e:
                        current_app.logger.error(f"Failed to send email to {email}: {str(e)}", exc_info=True)
                        # Add a flash message to notify about the email failure
                        flash(f"Note: Email invitation to {email} couldn't be sent.", "warning")
        
        # Generate the plan from AI conversation before redirecting
        # This ensures we have the plan created from user-AI conversation
        if activity_description:
            # Create an initial plan based on the conversation
            planner.create_plan_from_description(activity_description, activity_type)
            
        # Redirect to participants page - changed flow as requested
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
    
    # Force reload participant data to ensure we're using the latest data
    db.session.refresh(participant)
    
    # Check if the completed flag was set (returning from final submission)
    completed = request.args.get('completed', 'false') == 'true'
    if completed:
        # Mark the participant as complete if they're not already
        if participant.status != 'complete':
            participant.status = 'complete'
            db.session.commit()
            current_app.logger.info(f"Updated participant {participant_id} status to 'complete' from query parameter")
        
        # Always pass all_complete as True if completed flag is present
        all_complete = True
    else:
        # Initialize planner and determine current status
        planner = ActivityPlanner(activity_id)
        
        # Retrieve participant preferences for display
        preferences = planner.get_participant_preferences(participant_id)
        
        # Check if participant is already marked as complete
        all_complete = participant.status == 'complete'
        
        # Only generate questions if not complete
        questions = None
        if not all_complete:
            questions = planner.generate_questions_batch(participant_id)
            # If no more questions, this also means they're complete
            all_complete = questions is None
            if all_complete and participant.status != 'complete':
                participant.status = 'complete'
                db.session.commit()
                current_app.logger.info(f"Updated participant {participant_id} status to 'complete' from question check")
    
    # Check if we should use conversational interface
    use_conversation = request.args.get('conversation', 'false') == 'true'
    
    # Fetch participant preferences for the template
    planner = ActivityPlanner(activity_id)
    preferences = planner.get_participant_preferences(participant_id)
    
    # Log the participant status
    current_app.logger.info(f"Rendering questions for participant {participant_id} with status {participant.status}, all_complete={all_complete}")

    return render_template(
        'questions.html',
        activity=activity,
        participant=participant,
        questions=questions if 'questions' in locals() else None,
        all_complete=all_complete,
        use_conversation=use_conversation,
        preferences=preferences
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
    data = request.json
    current_app.logger.info(f"Received data: {data}")
    
    # Get answers - could be a flat dict or an object with category structure
    answers = data.get('answers', {})
    if not answers:
        current_app.logger.warning(f"No answers submitted for participant {participant_id}")
        return jsonify({"error": "No answers provided"}), 400
    
    # Check if this is a final submission
    is_final = data.get('is_final', False)
    current_app.logger.info(f"Is final submission: {is_final}")
    
    # Save answers as preferences
    planner = ActivityPlanner(activity_id)
    
    # Check if we have a new structure with categories already defined
    if isinstance(answers, dict) and any(key in ['contact', 'activity', 'timing', 'group', 'meals', 'requirements'] for key in answers.keys()):
        # New structure - iterate through categories
        for category, prefs in answers.items():
            if not isinstance(prefs, dict):
                continue
                
            for question_id, answer in prefs.items():
                if not answer:  # Skip empty answers
                    continue
                    
                # Log the preference being saved
                current_app.logger.info(f"Saving preference: {category}.{question_id} = {answer}")
                
                # Save the preference
                planner.save_preference(participant_id, category, question_id, answer)
                
                # Update participant record for special fields
                if category == 'contact':
                    if question_id == 'email':
                        participant.email = answer
                    elif question_id == 'name':
                        participant.name = answer
                    elif question_id == 'allow_group_text':
                        participant.allow_group_text = answer
    else:
        # Old structure - determine category from question ID
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
    if is_final:
        participant.status = 'complete'
        db.session.commit()
        current_app.logger.info(f"Updated participant {participant_id} status to 'complete' from final submission")
    else:
        participant.status = 'active'
        db.session.commit()
        current_app.logger.info(f"Updated participant {participant_id} status to 'active'")
    
    # Force database refresh before getting next questions
    db.session.refresh(participant)
    
    # Get next batch of questions only if not final submission
    next_questions = None
    if not is_final:
        current_app.logger.info(f"Getting next question batch for participant {participant_id}")
        next_questions = planner.generate_questions_batch(participant_id)
        
        # Log the next questions or completion
        if next_questions is None:
            current_app.logger.info(f"No more questions for participant {participant_id}")
            participant.status = 'complete'
            db.session.commit()
            current_app.logger.info(f"Updated participant {participant_id} status to 'complete' from no more questions")
        else:
            current_app.logger.info(f"Next batch has {len(next_questions)} questions")
    
    # Prepare response
    response_data = {
        "success": True,
        "next_questions": next_questions,
        "complete": is_final or next_questions is None
    }
    
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
    current_app.logger.info(f"Processing feedback for activity ID: {activity_id}")
    activity = Activity.query.get_or_404(activity_id)
    
    # Get the most recent plan
    plan = Plan.query.filter_by(activity_id=activity_id).order_by(Plan.created_at.desc()).first()
    if not plan:
        current_app.logger.warning(f"No plan found for activity {activity_id}")
        flash("No plan has been generated yet.", "warning")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    current_app.logger.info(f"Found plan: {plan.id} (status: {plan.status})")
    
    # Get the participant from session
    participant_id = session.get(f'activity_{activity_id}_participant')
    if not participant_id:
        current_app.logger.warning(f"No participant ID in session for activity {activity_id}")
        flash("Please access this page through your invitation link.", "error")
        return redirect(url_for('main.index'))
    
    current_app.logger.info(f"Participant ID from session: {participant_id}")
    
    participant = Participant.query.get(participant_id)
    if not participant or participant.activity_id != activity_id:
        current_app.logger.warning(f"Invalid participant {participant_id} for activity {activity_id}")
        flash("Invalid participant access.", "error")
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Process feedback
        feedback = request.form.get('feedback')
        
        if feedback:
            # Initialize planner and revise plan
            planner = ActivityPlanner(activity_id)
            
            # First save the feedback as a preference to ensure it's stored
            current_app.logger.info(f"Saving feedback preference for activity {activity_id}, participant {participant_id}: {feedback[:50]}...")
            planner.save_preference(participant_id, 'feedback', 'plan_feedback', feedback)
            
            # Verify the preference was saved
            prefs = Preference.query.filter_by(
                activity_id=activity_id,
                participant_id=participant_id,
                category='feedback',
                key='plan_feedback'
            ).all()
            current_app.logger.info(f"After saving, found {len(prefs)} feedback preferences")
            
            # Then revise the plan
            revised_plan = planner.revise_plan(plan.id, feedback, participant_id=participant_id)
            
            flash("Thank you for your feedback! The plan has been updated.", "success")
            
            # Email notifications for activity updates are disabled
            # Only the participant who submitted feedback will be notified
            
            # Send SMS notifications to participants who opted in
            for p in activity.participants:
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
    
@main_bp.route('/activity/<activity_id>/add-test-feedback/<participant_id>', methods=['GET'])
def add_test_feedback(activity_id, participant_id):
    """Add test feedback for debugging purposes."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Get the participant
    participant = Participant.query.get_or_404(participant_id)
    if participant.activity_id != activity_id:
        return jsonify({"error": "Participant does not belong to this activity"}), 400
    
    # Get the most recent plan
    plan = Plan.query.filter_by(activity_id=activity_id).order_by(Plan.created_at.desc()).first()
    if not plan:
        return jsonify({"error": "No plan found for this activity"}), 404
    
    # Add test feedback
    planner = ActivityPlanner(activity_id)
    test_feedback = f"This is test feedback added for debugging purposes at {datetime.now()}."
    
    # Save the feedback directly
    planner.save_preference(participant_id, 'feedback', 'plan_feedback', test_feedback)
    
    # Check if it was saved
    prefs = Preference.query.filter_by(
        activity_id=activity_id,
        participant_id=participant_id,
        category='feedback',
        key='plan_feedback'
    ).all()
    
    return jsonify({
        "success": True,
        "message": f"Test feedback added for participant {participant_id}",
        "preferences_saved": len(prefs),
        "feedback": test_feedback
    })
@main_bp.route('/activity/<activity_id>/process-input', methods=['POST'])
def process_conversation_input(activity_id):
    """Process conversational input and generate a plan."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Get the input from the form
    input_text = request.form.get('input_text', '')
    
    if not input_text:
        flash("Please provide some details about your activity.", "warning")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    # Initialize planner and process input
    planner = ActivityPlanner(activity_id)
    plan = planner.process_conversation_input(input_text)
    
    # Redirect to the plan
    flash("Plan generated based on your input!", "success")
    return redirect(url_for('main.view_plan', activity_id=activity_id))

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

@main_bp.route('/activity/<activity_id>/add-participants', methods=['POST'])
@login_required
def add_participants(activity_id):
    """Add additional participants to an existing activity."""
    # Verify activity belongs to current user
    activity = Activity.query.get_or_404(activity_id)
    if activity.creator_id != current_user.id:
        flash("You don't have permission to do that.", "error")
        return redirect(url_for('main.dashboard'))
    
    # Get participant data from form
    participant_phones = request.form.getlist('participant_phone[]')
    participant_emails = request.form.getlist('participant_email[]')
    participant_names = request.form.getlist('participant_name[]')
    
    # Initialize planner
    planner = ActivityPlanner(activity_id)
    
    # Count successful invitations
    success_count = 0
    
    # Add each participant and send invitation
    for i in range(len(participant_phones)):
        if participant_phones[i]:
            phone = participant_phones[i]
            email = participant_emails[i] if i < len(participant_emails) else None
            name = participant_names[i] if i < len(participant_names) else None
            
            try:
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
                    current_app.logger.info(f"Attempting to send SMS to {phone} for activity {activity.id}")
                    result = sms_service.send_welcome_message(phone, activity.id, participant.id)
                    current_app.logger.info(f"SMS sent successfully to {phone}: {result}")
                except Exception as e:
                    current_app.logger.error(f"Failed to send SMS to {phone}: {str(e)}", exc_info=True)
                    # Add a flash message to notify about the SMS failure
                    flash(f"Note: SMS invitation to {phone} couldn't be sent. Participants can still be invited manually.", "warning")
                
                # Send email invitation if available
                if email:
                    try:
                        current_app.logger.info(f"Attempting to send email to {email} for activity {activity.id}")
                        email_service.send_welcome_email(
                            email,
                            name or "Participant",
                            activity.id,
                            participant.id
                        )
                        current_app.logger.info(f"Email sent successfully to {email}")
                    except Exception as e:
                        current_app.logger.error(f"Failed to send email to {email}: {str(e)}", exc_info=True)
                        # Add a flash message to notify about the email failure
                        flash(f"Note: Email invitation to {email} couldn't be sent.", "warning")
                
                success_count += 1
            except Exception as e:
                current_app.logger.error(f"Failed to add participant {name or phone}: {str(e)}")
    
    if success_count > 0:
        flash(f"Successfully invited {success_count} new participant(s)!", "success")
    else:
        flash("No participants were added. Please check your inputs and try again.", "warning")
    
    return redirect(url_for('main.activity_detail', activity_id=activity_id))

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
                text('DELETE FROM preferences WHERE participant_id = :participant_id'),
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

@main_bp.route('/activity/<activity_id>/generate-claude-plan')
def generate_claude_plan(activity_id):
    """Generate an activity plan using Claude."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Initialize planner
    planner = ActivityPlanner(activity_id)
    
    try:
        # Collect all preferences
        all_preferences = planner.get_all_preferences()
        
        # Generate plan with Claude
        result = claude_service.generate_activity_plan(activity_id, all_preferences)
        
        # Create the plan
        plan = planner.create_plan_from_claude(result)
        
        # Update activity status
        activity.status = 'planned'
        db.session.commit()
        
        flash("Plan generated successfully with AI assistance!", "success")
    except Exception as e:
        current_app.logger.error(f"Error generating plan with Claude: {str(e)}")
        flash(f"Error generating plan: {str(e)}", "error")
    
    # Redirect to plan page
    return redirect(url_for('main.view_plan', activity_id=activity_id))

@main_bp.route('/activity/<activity_id>/conversation-planner')
@login_required
def conversation_planner(activity_id):
    """Conversation-based activity planning interface."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Verify activity belongs to current user
    if activity.creator_id != current_user.id:
        flash("You don't have permission to do that.", "error")
        return redirect(url_for('main.dashboard'))
    
    return render_template('conversation_planner.html', activity=activity)

@main_bp.route('/activity/<activity_id>/manage-feedback')
@login_required
def manage_feedback(activity_id):
    """Activity feedback management page."""
    # Get the activity
    current_app.logger.info(f"Managing feedback for activity ID: {activity_id}")
    activity = Activity.query.get_or_404(activity_id)
    
    # Verify activity belongs to current user
    if activity.creator_id != current_user.id:
        current_app.logger.warning(f"User {current_user.id} tried to access activity {activity_id} but is not the creator")
        flash("You don't have permission to do that.", "error")
        return redirect(url_for('main.dashboard'))
    
    # Get the most recent plan
    plan = Plan.query.filter_by(activity_id=activity_id).order_by(Plan.created_at.desc()).first()
    if not plan:
        flash("No plan has been generated yet for this activity.", "warning")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    # Get all feedback for this activity
    feedback_list = Preference.get_feedback_for_activity(activity_id)
    
    # Log what feedback we found for debugging
    current_app.logger.info(f"Found {len(feedback_list)} feedback entries for activity {activity_id}")
    for feedback in feedback_list:
        current_app.logger.info(f"  - Feedback from {feedback['participant_name']}: {feedback['feedback'][:50]}...")
    
    # Get all feedback preferences directly for debugging
    all_feedback_prefs = Preference.query.filter_by(
        activity_id=activity_id, 
        category='feedback'
    ).all()
    current_app.logger.info(f"Direct query found {len(all_feedback_prefs)} feedback preferences")
    for pref in all_feedback_prefs:
        current_app.logger.info(f"  - Preference {pref.id}: category={pref.category}, key={pref.key}, value={pref.value[:50] if pref.value else None}...")
    
    # Get AI suggestions if available
    ai_suggestions = AISuggestion.query.filter_by(
        plan_id=plan.id
    ).order_by(AISuggestion.created_at.desc()).first()
    
    return render_template(
        'feedback_management.html',
        activity=activity,
        plan=plan,
        feedback_list=feedback_list,
        ai_suggestions=ai_suggestions
    )

@main_bp.route('/activity/<activity_id>/plan/<plan_id>/analyze_feedback', methods=['POST'])
@login_required
def analyze_feedback(activity_id, plan_id):
    """Analyze feedback for a plan and generate AI suggestions."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Verify activity belongs to current user
    if activity.creator_id != current_user.id:
        return jsonify({"success": False, "error": "You don't have permission to do that."}), 403
    
    # Get the plan
    plan = Plan.query.get_or_404(plan_id)
    if plan.activity_id != activity_id:
        return jsonify({"success": False, "error": "Invalid plan for this activity."}), 400
    
    try:
        # Initialize planner
        planner = ActivityPlanner(activity_id)
        
        # Call Claude to analyze feedback
        current_app.logger.info(f"Analyzing feedback for plan {plan_id} with Claude AI")
        suggestion = planner.analyze_feedback_with_claude(plan_id)
        
        return jsonify({
            "success": True,
            "suggestion_id": suggestion.id
        })
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing feedback: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@main_bp.route('/activity/<activity_id>/plan/<plan_id>/apply_ai_suggestions', methods=['POST'])
@login_required
def apply_ai_suggestions(activity_id, plan_id):
    """Apply AI suggestions to create a new plan version."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Verify activity belongs to current user
    if activity.creator_id != current_user.id:
        flash("You don't have permission to do that.", "error")
        return redirect(url_for('main.dashboard'))
    
    # Get the plan
    plan = Plan.query.get_or_404(plan_id)
    if plan.activity_id != activity_id:
        flash("Invalid plan for this activity.", "error")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    # Get the suggestion ID from form
    suggestion_id = request.form.get('suggestion_id')
    if not suggestion_id:
        flash("No suggestion ID provided.", "error")
        return redirect(url_for('main.manage_feedback', activity_id=activity_id))
    
    try:
        # Initialize planner
        planner = ActivityPlanner(activity_id)
        
        # Apply the suggestions
        current_app.logger.info(f"Applying AI suggestion {suggestion_id} to plan {plan_id}")
        revised_plan = planner.apply_ai_suggestions(suggestion_id)
        
        flash("AI suggestions applied successfully!", "success")
        return redirect(url_for('main.view_plan', activity_id=activity_id))
        
    except Exception as e:
        current_app.logger.error(f"Error applying AI suggestions: {str(e)}", exc_info=True)
        flash(f"Error applying suggestions: {str(e)}", "error")
        return redirect(url_for('main.manage_feedback', activity_id=activity_id))

@main_bp.route('/activity/<activity_id>/plan/<plan_id>/update_plan_manually', methods=['POST'])
@login_required
def update_plan_manually(activity_id, plan_id):
    """Update a plan manually with provided data."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Verify activity belongs to current user
    if activity.creator_id != current_user.id:
        flash("You don't have permission to do that.", "error")
        return redirect(url_for('main.dashboard'))
    
    # Get the plan
    plan = Plan.query.get_or_404(plan_id)
    if plan.activity_id != activity_id:
        flash("Invalid plan for this activity.", "error")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    try:
        # Initialize planner
        planner = ActivityPlanner(activity_id)
        
        # Update the plan with form data
        current_app.logger.info(f"Manually updating plan {plan_id}")
        
        # Process the form data
        updated_data = {
            'plan_title': request.form.get('plan_title'),
            'plan_description': request.form.get('plan_description'),
            'scheduled_date': request.form.get('scheduled_date'),
            'start_time': request.form.get('start_time'),
            'time_window': request.form.get('time_window'),
            'location_address': request.form.get('location_address')
        }
        
        # Update the plan
        revised_plan = planner.update_plan_manually(plan_id, updated_data)
        
        flash("Plan updated successfully!", "success")
        return redirect(url_for('main.view_plan', activity_id=activity_id))
        
    except Exception as e:
        current_app.logger.error(f"Error updating plan: {str(e)}", exc_info=True)
        flash(f"Error updating plan: {str(e)}", "error")
        return redirect(url_for('main.manage_feedback', activity_id=activity_id))

@main_bp.route('/activity/<activity_id>/plan/<plan_id>/request_plan_approval', methods=['POST'])
@login_required
def request_plan_approval(activity_id, plan_id):
    """Request approval from all participants for a plan."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Verify activity belongs to current user
    if activity.creator_id != current_user.id:
        flash("You don't have permission to do that.", "error")
        return redirect(url_for('main.dashboard'))
    
    # Get the plan
    plan = Plan.query.get_or_404(plan_id)
    if plan.activity_id != activity_id:
        flash("Invalid plan for this activity.", "error")
        return redirect(url_for('main.activity_detail', activity_id=activity_id))
    
    try:
        # Initialize planner
        planner = ActivityPlanner(activity_id)
        
        # Request approval
        current_app.logger.info(f"Requesting approval for plan {plan_id}")
        planner.request_plan_approval(plan_id)
        
        # Notify all participants about the approval request
        participants = Participant.query.filter_by(activity_id=activity_id).all()
        
        for participant in participants:
            # Skip participants without contact information
            if not participant.email and not participant.phone_number:
                continue
            
            # Send email notification if available
            if participant.email:
                try:
                    email_service.send_email(
                        participant.email,
                        "The activity plan requires your approval",
                        f"Hello {participant.name or 'Participant'},<br><br>The organizer of '{activity.title}' has updated the plan and would like your approval. Please check your email for details or visit the activity page to review and approve the plan."
                    )
                except Exception as e:
                    current_app.logger.error(f"Failed to send approval email to {participant.email}: {str(e)}")
            
            # Send SMS notification if they opted in
            if participant.allow_group_text and participant.phone_number:
                try:
                    sms_service.send_notification(
                        participant.phone_number,
                        "The activity plan has been updated and requires your approval. Check your email for details.",
                        activity_id
                    )
                except Exception as e:
                    current_app.logger.error(f"Failed to send approval SMS to {participant.phone_number}: {str(e)}")
        
        flash("Approval requests sent to all participants!", "success")
        return redirect(url_for('main.view_plan', activity_id=activity_id))
        
    except Exception as e:
        current_app.logger.error(f"Error requesting plan approval: {str(e)}", exc_info=True)
        flash(f"Error requesting approval: {str(e)}", "error")
        return redirect(url_for('main.manage_feedback', activity_id=activity_id))