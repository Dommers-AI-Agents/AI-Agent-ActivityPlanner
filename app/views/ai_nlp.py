"""
Routes for supporting AI natural language processing with Claude integration in the Group Activity Planner.
"""
from flask import Blueprint, request, jsonify, current_app, session
from app.models.database import Activity, Participant, Preference
from app.models.planner import ActivityPlanner
from app.services.claude_service import claude_service
from app import db
import json
import logging
import os

logger = logging.getLogger(__name__)

ai_nlp_bp = Blueprint('ai_nlp', __name__)

@ai_nlp_bp.route('/process_activity_input', methods=['POST'])
def process_activity_input():
    """Process natural language input from the activity creator using Claude."""
    data = request.json
    if not data or 'message' not in data:
        return jsonify({'error': 'Missing message content'}), 400
    
    message = data['message']
    conversation_history = data.get('conversation_history', [])
    
    try:
        # Process with Claude
        result = claude_service.process_activity_creator_input(message, conversation_history)
        
        # Log extracted information
        logger.info(f"Extracted activity info: {result.get('extracted_info', {})}")
        
        # Store in session for later use when creating the activity
        if 'extracted_activity_info' not in session:
            session['extracted_activity_info'] = {}
        
        # Update extracted info with new information
        extracted_info = result.get('extracted_info', {})
        for key, value in extracted_info.items():
            if value:  # Only update if we have a value
                session['extracted_activity_info'][key] = value
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error processing activity input: {str(e)}")
        return jsonify({
            'error': 'Failed to process input',
            'message': 'I encountered an error processing your message. Please try again.'
        }), 500

@ai_nlp_bp.route('/planner/converse', methods=['POST'])
def planner_converse():
    """Handle conversational input for activity planning."""
    data = request.json
    if not data or 'input' not in data:
        return jsonify({'error': 'Missing input data'}), 400
    
    input_text = data['input']
    conversation_history = data.get('conversation_history', [])
    
    logger.info(f"Processing input with Claude: {input_text[:100]}...")
    
    # Check if Claude is available
    api_key = current_app.config.get('ANTHROPIC_API_KEY') or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({
            'success': False,
            'message': "Claude AI is currently unavailable. Please try again later.",
            'error': "API key not configured"
        }), 503
    
    try:
        # Process with Claude
        result = claude_service.process_activity_creator_input(input_text, conversation_history)
        
        # Enhanced logging for debugging
        logger.info(f"Claude response type: {type(result)}")
        logger.info(f"Claude response: {result}")
        
        # Extract message and info
        final_message = ""
        extracted_info = {}
        
        # Handle different response types
        if isinstance(result, dict):
            # Direct dictionary response
            final_message = result.get('message', '')
            extracted_info = result.get('extracted_info', {})
        elif isinstance(result, str):
            # String response - check if it's JSON
            if result.strip().startswith('{') and '"message"' in result:
                try:
                    parsed = json.loads(result)
                    final_message = parsed.get('message', result)
                    extracted_info = parsed.get('extracted_info', {})
                except json.JSONDecodeError:
                    # Not valid JSON, use as-is
                    final_message = result
            else:
                # Regular string, use as-is
                final_message = result
        else:
            # Fallback for unexpected types
            final_message = str(result)
            
        # Create a clean response
        response = {
            'success': True,
            'message': final_message,
            'extracted_info': extracted_info
        }
        
        # Add plan if activity is trip-like
        if (len(input_text) > 100 and 
            any(keyword in input_text.lower() for keyword in ['trip', 'itinerary', 'museum', 'schedule', 'plan', 'visit'])):
            try:
                # Create a plan from mock data
                planner = ActivityPlanner()
                mock_plan = claude_service._mock_generate_plan({})
                response['plan'] = mock_plan
            except Exception as e:
                logger.error(f"Failed to generate plan: {str(e)}")
        
        logger.info(f"Final response: {response['message'][:100]}...")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in Claude conversation: {str(e)}")
        
        # Only use generic error message when Claude API call completely fails
        return jsonify({
            'success': False,
            'message': "There was an error connecting to the AI service. Please try again.",
            'error': str(e)
        }), 500

@ai_nlp_bp.route('/process_participant_input', methods=['POST'])
def process_participant_input():
    """Process natural language input from a participant using Claude."""
    data = request.json
    if not data or 'message' not in data or 'activity_id' not in data or 'participant_id' not in data:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    message = data['message']
    activity_id = data['activity_id']
    participant_id = data['participant_id']
    conversation_history = data.get('conversation_history', [])
    
    # Validate activity and participant
    activity = Activity.query.get(activity_id)
    participant = Participant.query.get(participant_id)
    
    if not activity or not participant or participant.activity_id != activity_id:
        return jsonify({'error': 'Invalid activity or participant ID'}), 404
    
    try:
        # Get activity info to provide context
        activity_info = {
            'title': activity.title,
            'description': activity.description,
            'status': activity.status
        }
        
        # Process with Claude
        result = claude_service.process_participant_input(
            message, 
            conversation_history, 
            activity_info
        )
        
        # Log extracted preferences
        logger.info(f"Extracted preferences: {result.get('extracted_preferences', {})}")
        
        # Save extracted preferences
        if result.get('extracted_preferences'):
            planner = ActivityPlanner(activity_id)
            preferences = result['extracted_preferences']
            
            for category, prefs in preferences.items():
                for key, value in prefs.items():
                    if value:  # Only save if we have a value
                        planner.save_preference(participant_id, category, key, value)
            
            # Update participant status
            if participant.status == 'invited':
                participant.status = 'active'
                db.session.commit()
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error processing participant input: {str(e)}")
        return jsonify({
            'error': 'Failed to process input',
            'message': 'I encountered an error processing your message. Please try again.'
        }), 500

@ai_nlp_bp.route('/generate_plan', methods=['POST'])
def generate_plan():
    """Generate an activity plan using Claude."""
    data = request.json
    if not data or 'activity_id' not in data:
        return jsonify({'error': 'Missing activity ID'}), 400
    
    activity_id = data['activity_id']
    
    # Validate activity
    activity = Activity.query.get(activity_id)
    if not activity:
        return jsonify({'error': 'Invalid activity ID'}), 404
    
    try:
        # Collect all preferences
        planner = ActivityPlanner(activity_id)
        all_preferences = planner.get_all_preferences()
        
        # Generate plan with Claude
        result = claude_service.generate_activity_plan(activity_id, all_preferences)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': 'Failed to generate activity plan'
            }), 500
        
        # Create the plan in the database
        plan = planner.create_plan_from_claude(result)
        
        return jsonify({
            'success': True,
            'plan_id': plan.id,
            'plan': plan.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error generating plan: {str(e)}")
        return jsonify({
            'error': 'Failed to generate plan',
            'message': f'I encountered an error generating the plan: {str(e)}'
        }), 500

@ai_nlp_bp.route('/transcribe_audio', methods=['POST'])
def transcribe_audio():
    """Transcribe audio using a speech-to-text service."""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    
    # In a real implementation, you would:
    # 1. Save the audio to a temporary file
    # 2. Use a speech-to-text service API
    # 3. Return the transcription
    
    try:
        # This is a placeholder. In a real implementation, you would call a speech-to-text service
        # For example, you might use Google Speech-to-Text, AWS Transcribe, etc.
        
        # For demonstration purposes, we're returning a mock response
        return jsonify({
            'success': True,
            'transcription': 'This is a simulated transcription of the audio. In a real implementation, you would use a speech-to-text service.'
        })
    
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return jsonify({
            'error': 'Failed to transcribe audio',
            'message': 'I encountered an error processing the audio recording.'
        }), 500

@ai_nlp_bp.route('/synthesize_speech', methods=['POST'])
def synthesize_speech():
    """Convert text to speech."""
    data = request.json
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing text to synthesize'}), 400
    
    text = data['text']
    
    # In a real implementation, you would:
    # 1. Use a text-to-speech service API to convert the text to audio
    # 2. Return the audio file or a URL to stream it
    
    try:
        # This is a placeholder. In a real implementation, you would call a text-to-speech service
        # For example, you might use Google Text-to-Speech, AWS Polly, etc.
        
        # For demonstration purposes, we're returning a mock response
        # In a real implementation, you might return a URL to an audio file
        return jsonify({
            'success': True,
            'message': 'Speech synthesis is supported through the browser\'s Web Speech API. For server-side synthesis, configure a TTS service.'
        })
    
    except Exception as e:
        logger.error(f"Error synthesizing speech: {str(e)}")
        return jsonify({
            'error': 'Failed to synthesize speech',
            'message': 'I encountered an error converting text to speech.'
        }), 500

@ai_nlp_bp.route('/test-claude', methods=['GET'])
def test_claude():
    """Test endpoint to directly call the Claude API."""
    import requests
    import os
    import json
    
    logger.info("Testing Claude API connection...")
    
    # Hardcoded API key for testing
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    api_url = "https://api.anthropic.com/v1/messages"
    model = "claude-3-opus-20240229"
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    data = {
        "model": model,
        "system": "You are a helpful assistant that keeps responses very brief.",
        "messages": [{"role": "user", "content": "Hello, Claude! This is a test message."}],
        "max_tokens": 100
    }
    
    logger.info(f"API Request: {json.dumps(data)}")
    logger.info(f"Headers: {headers}")
    
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=data,
            timeout=30
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text[:1000]}")
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'response': result,
                'message': "Claude API test successful!"
            })
        else:
            return jsonify({
                'success': False,
                'status_code': response.status_code,
                'response_text': response.text,
                'message': "Claude API test failed!"
            }), 500
    
    except Exception as e:
        logger.error(f"Error testing Claude API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        return jsonify({
            'success': False,
            'error': str(e),
            'message': "Exception while testing Claude API!"
        }), 500
