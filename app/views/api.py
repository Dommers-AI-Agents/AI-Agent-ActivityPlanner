"""
API routes for the Group Activity Planner.
"""
from flask import Blueprint, request, jsonify, current_app, abort
from app.models.database import Activity, Participant, Plan
from app.models.planner import ActivityPlanner
from app.services.sms_service import sms_service
from app.services.email_service import email_service
from app import db

api_bp = Blueprint('api', __name__)

@api_bp.route('/webhook/sms', methods=['POST'])
def sms_webhook():
    """Handle incoming SMS messages from Twilio."""
    # Verify this is a legitimate Twilio request in production
    # https://www.twilio.com/docs/usage/webhooks/webhooks-security
    
    # Get the incoming message details
    from_number = request.form.get('From')
    body = request.form.get('Body', '').strip()
    
    if not from_number or not body:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Find the participant by phone number
    participant = Participant.query.filter_by(phone_number=from_number).order_by(Participant.created_at.desc()).first()
    
    if not participant:
        # New participant, send a generic response
        response = "Thank you for your message! Please use the web interface to interact with the Group Activity Planner."
    else:
        # Process the message
        try:
            # Get the activity
            activity = Activity.query.get(participant.activity_id)
            
            # Handle as incoming message
            response = sms_service.handle_incoming_message(from_number, body)
            
            # Save the message
            from app.models.database import Message
            message = Message(
                activity_id=participant.activity_id,
                participant_id=participant.id,
                direction='incoming',
                channel='sms',
                content=body
            )
            db.session.add(message)
            
            # Save outgoing response
            response_message = Message(
                activity_id=participant.activity_id,
                participant_id=participant.id,
                direction='outgoing',
                channel='sms',
                content=response
            )
            db.session.add(response_message)
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Error processing SMS: {e}")
            response = "Sorry, an error occurred. Please try again later or use the web interface."
    
    # Respond to Twilio with TwiML
    return f"""
    <?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Message>{response}</Message>
    </Response>
    """

@api_bp.route('/activities/<activity_id>/converse', methods=['POST'])
def converse_with_planner(activity_id):
    """Handle conversational input for planning using Claude AI."""
    from app.services.claude_service import claude_service
    
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Get the input from request
    data = request.json
    if not data or 'input' not in data:
        return jsonify({'error': 'Missing input data'}), 400
    
    input_text = data['input']
    
    # Initialize planner
    planner = ActivityPlanner(activity_id)
    
    try:
        # Process with Claude API
        current_app.logger.info(f"Processing input with Claude: {input_text[:100]}...")
        
        # Get conversation history if any
        conversation_history = planner.get_claude_conversation()
        
        # Save the user's message to the conversation
        planner.save_conversation_message(input_text, is_user=True)
        
        # Process with Claude
        claude_response = planner.process_claude_input(input_text, conversation_history=conversation_history)
        
        # Check if Claude could generate a response
        if not claude_response or 'message' not in claude_response:
            current_app.logger.warning("Claude API returned an empty or invalid response")
            # Fall back to basic plan generation
            plan = planner.generate_quick_plan(input_text)
            
            # Save a fallback message
            planner.save_conversation_message(
                "I've created a basic plan based on your input. Please let me know if you'd like to adjust anything.", 
                is_user=False
            )
        else:
            # Extract structured information from Claude's response and generate plan
            current_app.logger.info("Claude extracted information, generating plan")
            
            # Create a plan with Claude's guidance
            # Use extracted_info if available
            if 'extracted_info' in claude_response and claude_response['extracted_info']:
                plan = planner.generate_quick_plan(input_text)
            else:
                # Just use the basic plan generation if no structured info
                plan = planner.generate_quick_plan(input_text)
        
        return jsonify({
            'success': True,
            'activity_id': activity_id,
            'plan_id': plan.id,
            'plan': plan.to_dict(),
            'message': claude_response.get('message', "I've created a plan based on your input. How does this look?")
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in Claude conversation: {str(e)}")
        
        # Fall back to basic plan generation
        try:
            plan = planner.generate_quick_plan(input_text)
            
            return jsonify({
                'success': True,
                'activity_id': activity_id,
                'plan_id': plan.id,
                'plan': plan.to_dict(),
                'message': "I had some trouble understanding all the details, but I've created a basic plan based on what I understood. Let me know if you'd like to adjust anything."
            })
        except Exception as fallback_error:
            current_app.logger.error(f"Fallback plan generation failed: {str(fallback_error)}")
            return jsonify({
                'success': False,
                'error': 'Failed to process input and generate plan'
            }), 500

@api_bp.route('/activities/<activity_id>/participants', methods=['POST'])
def add_participants(activity_id):
    """Add participants to an activity."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Get the participants data from request
    data = request.json
    if not data or 'participants' not in data:
        return jsonify({'error': 'Missing participants data'}), 400
    
    participants = data['participants']
    results = []
    
    # Initialize planner
    planner = ActivityPlanner(activity_id)
    
    # Add each participant
    for p in participants:
        if 'phone_number' not in p:
            results.append({
                'error': 'Missing phone number',
                'data': p
            })
            continue
        
        try:
            # Add the participant
            participant = planner.add_participant(
                phone_number=p['phone_number'],
                email=p.get('email'),
                name=p.get('name')
            )
            
            # Send SMS invitation
            if 'skip_sms' not in p or not p['skip_sms']:
                sms_service.send_welcome_message(p['phone_number'], activity_id, participant.id)
            
            # Send email invitation if available
            if 'email' in p and p['email'] and ('skip_email' not in p or not p['skip_email']):
                email_service.send_welcome_email(
                    p['email'],
                    p.get('name', 'Participant'),
                    activity_id,
                    participant.id
                )
            
            results.append({
                'success': True,
                'participant_id': participant.id,
                'phone_number': p['phone_number']
            })
            
        except Exception as e:
            current_app.logger.error(f"Error adding participant: {e}")
            results.append({
                'error': str(e),
                'data': p
            })
    
    return jsonify({
        'activity_id': activity_id,
        'results': results
    })

@api_bp.route('/activities/<activity_id>/participants/<participant_id>/preferences', methods=['GET'])
def get_preferences(activity_id, participant_id):
    """Get preferences for a participant."""
    # Verify the participant exists and belongs to the activity
    participant = Participant.query.get_or_404(participant_id)
    if participant.activity_id != activity_id:
        abort(404)
    
    # Initialize planner
    planner = ActivityPlanner(activity_id)
    
    # Get preferences
    preferences = planner.get_participant_preferences(participant_id)
    
    return jsonify({
        'activity_id': activity_id,
        'participant_id': participant_id,
        'preferences': preferences
    })

@api_bp.route('/activities/<activity_id>/participants/<participant_id>/preferences', methods=['POST'])
def save_preferences(activity_id, participant_id):
    """Save preferences for a participant."""
    # Verify the participant exists and belongs to the activity
    participant = Participant.query.get_or_404(participant_id)
    if participant.activity_id != activity_id:
        abort(404)
    
    # Get the preferences data from request
    data = request.json
    if not data or 'preferences' not in data:
        return jsonify({'error': 'Missing preferences data'}), 400
    
    preferences = data['preferences']
    
    # Initialize planner
    planner = ActivityPlanner(activity_id)
    
    # Save each preference
    for category, values in preferences.items():
        for key, value in values.items():
            planner.save_preference(participant_id, category, key, value)
    
    return jsonify({
        'success': True,
        'activity_id': activity_id,
        'participant_id': participant_id
    })

@api_bp.route('/activities/<activity_id>/generate-plan', methods=['POST'])
def api_generate_plan(activity_id):
    """Generate an activity plan."""
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Initialize planner and generate plan
    planner = ActivityPlanner(activity_id)
    plan = planner.generate_plan()
    
    # Process notification settings
    data = request.json or {}
    send_notifications = data.get('send_notifications', False)
    
    if send_notifications:
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
    
    return jsonify({
        'success': True,
        'activity_id': activity_id,
        'plan_id': plan.id,
        'plan': plan.to_dict()
    })

@api_bp.route('/activities/<activity_id>/plans/<plan_id>/feedback', methods=['POST'])
def api_submit_feedback(activity_id, plan_id):
    """Submit feedback on the plan."""
    # Verify the plan exists and belongs to the activity
    plan = Plan.query.get_or_404(plan_id)
    if plan.activity_id != activity_id:
        abort(404)
    
    # Get the feedback data from request
    data = request.json
    if not data or 'feedback' not in data:
        return jsonify({'error': 'Missing feedback data'}), 400
    
    feedback = data['feedback']
    participant_id = data.get('participant_id')
    
    # Verify the participant exists and belongs to the activity
    if participant_id:
        participant = Participant.query.get_or_404(participant_id)
        if participant.activity_id != activity_id:
            abort(404)
    
    # Initialize planner and revise plan
    planner = ActivityPlanner(activity_id)
    revised_plan = planner.revise_plan(plan_id, feedback)
    
    # Save the feedback as a preference if participant_id is provided
    if participant_id:
        planner.save_preference(participant_id, 'feedback', 'plan_feedback', feedback)
    
    # Process notification settings
    send_notifications = data.get('send_notifications', False)
    
    if send_notifications:
        activity = Activity.query.get(activity_id)
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
    
    return jsonify({
        'success': True,
        'activity_id': activity_id,
        'plan_id': revised_plan.id,
        'plan': revised_plan.to_dict()
    })

@api_bp.route('/activities/<activity_id>/plans/<plan_id>/finalize', methods=['POST'])
def api_finalize_plan(activity_id, plan_id):
    """Finalize the activity plan."""
    # Verify the plan exists and belongs to the activity
    plan = Plan.query.get_or_404(plan_id)
    if plan.activity_id != activity_id:
        abort(404)
    
    # Get the activity
    activity = Activity.query.get_or_404(activity_id)
    
    # Update plan status
    plan.status = 'final'
    activity.status = 'finalized'
    db.session.commit()
    
    # Process notification settings
    data = request.json or {}
    send_notifications = data.get('send_notifications', False)
    
    if send_notifications:
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
    
    return jsonify({
        'success': True,
        'activity_id': activity_id,
        'plan_id': plan.id,
        'plan': plan.to_dict()
    })
