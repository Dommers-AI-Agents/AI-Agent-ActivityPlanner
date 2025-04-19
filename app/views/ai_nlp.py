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
import re

logger = logging.getLogger(__name__)

def process_claude_response(raw_response):
    """Process and clean Claude API responses for display to users.
    
    Args:
        raw_response: The raw response from Claude API (can be string, dict, etc.)
        
    Returns:
        dict: A cleaned and structured response with consistent format:
            {
                'message': Clean natural language message for the user,
                'extracted_info': Dictionary of extracted data (if any),
                'plan': Structured plan data (if any),
                'success': Boolean indicating if processing was successful
            }
    """
    logger.info(f"Processing Claude response of type: {type(raw_response)}")
    
    # Initialize the result structure
    result = {
        'message': '',
        'extracted_info': {},
        'plan': None,
        'success': True
    }
    
    try:
        # Handle string responses
        if isinstance(raw_response, str):
            logger.debug(f"Processing string response: {raw_response[:100]}...")
            
            # Check if the string is JSON
            if raw_response.strip().startswith('{') and '"message"' in raw_response:
                try:
                    parsed_json = json.loads(raw_response)
                    logger.debug(f"Successfully parsed JSON from string response")
                    
                    # Extract message
                    if 'message' in parsed_json:
                        result['message'] = parsed_json['message']
                    
                    # Extract other fields if available
                    if 'extracted_info' in parsed_json:
                        result['extracted_info'] = parsed_json['extracted_info']
                    
                    if 'plan' in parsed_json:
                        result['plan'] = parsed_json['plan']
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from string: {e}")
                    # Still use the original string as message
                    result['message'] = raw_response
            else:
                # Not JSON, use as-is
                result['message'] = raw_response
        
        # Handle dictionary responses
        elif isinstance(raw_response, dict):
            logger.debug(f"Processing dictionary response with keys: {raw_response.keys()}")
            
            # Extract message from the response
            if 'message' in raw_response:
                message = raw_response['message']
                
                # Check if the message is a JSON string
                if isinstance(message, str) and message.strip().startswith('{') and '"message"' in message:
                    try:
                        # Parse nested JSON
                        nested_json = json.loads(message)
                        logger.debug(f"Found nested JSON in message field")
                        
                        if 'message' in nested_json:
                            result['message'] = nested_json['message']
                        
                        if 'extracted_info' in nested_json:
                            result['extracted_info'] = nested_json['extracted_info']
                    except json.JSONDecodeError:
                        # Use the original message if parsing fails
                        result['message'] = message
                else:
                    # Use message as-is
                    result['message'] = message
            
            # Handle error responses
            if 'error' in raw_response:
                logger.error(f"Error in Claude response: {raw_response['error']}")
                result['success'] = False
                if not result['message']:
                    result['message'] = f"Error: {raw_response['error']}"
            
            # Extract extracted_info if available
            if 'extracted_info' in raw_response:
                result['extracted_info'] = raw_response['extracted_info']
            
            # Extract plan if available 
            if 'plan' in raw_response:
                result['plan'] = raw_response['plan']
        
        # Handle unexpected types
        else:
            logger.warning(f"Unexpected response type: {type(raw_response)}")
            result['message'] = str(raw_response)
            
        # Clean the message
        result['message'] = _clean_claude_message(result['message'])
        
        return result
    
    except Exception as e:
        logger.error(f"Error processing Claude response: {str(e)}", exc_info=True)
        return {
            'message': "I apologize, but I encountered an error processing the response. Please try again.",
            'extracted_info': {},
            'plan': None,
            'success': False
        }

def _clean_claude_message(message):
    """Clean Claude's message for display.
    
    Args:
        message (str): The raw message from Claude
        
    Returns:
        str: The cleaned message
    """
    if not isinstance(message, str):
        return str(message)
    
    # Remove any "```json" code blocks that might contain the response
    message = re.sub(r'```json\s*(.*?)\s*```', r'\1', message, flags=re.DOTALL)
    
    # Remove any backslashes used to escape quotes
    message = message.replace('\\"', '"')
    
    # Handle escaped newlines
    message = message.replace('\\n', '\n')
    
    # Try to extract message from any remaining JSON structure
    if message.strip().startswith('{') and '"message"' in message:
        try:
            # Use regex to extract just the message part
            message_match = re.search(r'"message"\s*:\s*"(.*?)"(?:,|\})', message, re.DOTALL)
            if message_match:
                extracted = message_match.group(1)
                # Unescape any remaining escaped characters
                extracted = extracted.replace('\\n', '\n').replace('\\"', '"')
                return extracted
        except Exception as e:
            logger.warning(f"Error extracting message from JSON with regex: {e}")
            
            # Try full JSON parsing if regex fails
            try:
                parsed = json.loads(message)
                if 'message' in parsed:
                    return parsed['message']
            except json.JSONDecodeError:
                # Keep original if both methods fail
                pass
    
    return message

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
        raw_result = claude_service.process_activity_creator_input(input_text, conversation_history)
        
        # Process the raw response into a clean, structured format
        result = process_claude_response(raw_result)
        
        # Enhanced logging for debugging
        logger.info(f"Claude response type: {type(raw_result)}")
        logger.info(f"Processed response: {result}")
        
        # Extract message and info
        final_message = result['message']
        extracted_info = result['extracted_info']
        
        # Create the response structure
        response = {
            'success': True,
            'message': final_message,
            'extracted_info': extracted_info
        }
        
        # Add plan if available from Claude
        if result.get('plan'):
            response['plan'] = result['plan']
        # Removed the mock museum plan injection that was overriding Claude's actual response
        
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
