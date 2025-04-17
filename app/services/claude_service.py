"""
Claude API integration service for the Group Activity Planner.
This service connects to the Anthropic Claude API to process natural language input.
"""
import os
import json
import requests
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class ClaudeService:
    """Service for interacting with the Anthropic Claude API."""
    
    def __init__(self, app=None):
        """Initialize the Claude service."""
        self.app = app
        self.api_key = None
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-opus-20240229"  # Default model, can be configured
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the service with a Flask app."""
        self.app = app
        
        # Try to get API key from environment or config
        env_key = os.environ.get('ANTHROPIC_API_KEY')
        config_key = app.config.get('ANTHROPIC_API_KEY')
        
        self.api_key = env_key or config_key
        self.model = app.config.get('CLAUDE_MODEL', self.model)
        
        if self.api_key:
            # Log obfuscated API key for confirmation
            first_chars = self.api_key[:5] if len(self.api_key) > 5 else "***"
            app.logger.info(f"Claude service initialized with API key: {first_chars}... Model: {self.model}")
        else:
            # Critical warning and fallback to mock service if no API key
            app.logger.warning("⚠️ ANTHROPIC_API_KEY not set. Claude integration will be MOCKED.")
            # Set a flag to use mock responses
            self.mock_mode = True
    
    def process_activity_creator_input(self, message, conversation_history=None):
        """Process natural language input from the activity creator.
        
        Args:
            message (str): The message from the activity creator.
            conversation_history (list, optional): Previous messages in the conversation.
            
        Returns:
            dict: Claude's response with extracted information.
        """
        # Check if we need to use mock mode
        if hasattr(self, 'mock_mode') and self.mock_mode:
            return self._mock_creator_response(message)
            
        # Construct the prompt with system instructions
        system_prompt = """
        You are an AI-powered Activity Planner that helps people plan group activities.
        
        Your role is to:
        1. Provide helpful, conversational responses that directly address the specific details provided by the user
        2. Extract structured information from messages to build a complete activity itinerary
        
        Important guidelines:
        - Always acknowledge the information the user has already provided
        - If the user provides detailed activity information (like a trip with group details), respond directly to that
        - Never ask for information the user has already provided
        - Never respond with a generic greeting if the user has provided activity details
        
        Key information to gather:
        1. Activity type (e.g., dinner, movie, hiking, museum visit, etc.)
        2. Group size and composition (adults, children, age ranges, relationships)
        3. Location specifics (departure, destination, venues, indoor/outdoor)
        4. Budget details (per person, total, specific mentions of costs)
        5. Timing information (date, time of day, duration, arrival/departure times)
        6. Transportation plans (method, vehicles, rental needs, public transport)
        7. Special requirements (accessibility, dietary restrictions, interests)
        8. Meal arrangements (included meals, restaurant preferences)
        
        Format your response as JSON with the following structure:
        {
            "message": "Your natural language response to the user that specifically references details they provided",
            "extracted_info": {
                "activity_type": "The specific type of activity mentioned or null",
                "group_size": "The number of people mentioned or null",
                "group_composition": "Details about who is in the group (adults, children, seniors, etc.) or null",
                "location": "Location details mentioned or null",
                "budget": "Budget information mentioned or null",
                "timing": "Time-related details (day, time, duration) or null",
                "transportation": "Transportation information mentioned or null",
                "special_requirements": "Any special requirements or considerations mentioned or null",
                "meals": "Meal preferences or arrangements mentioned or null",
                "duration": "How long the activity will last or null"
            }
        }
        """
        
        # Convert conversation history to Claude's format
        messages = []
        if conversation_history:
            for msg in conversation_history:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})
        
        # Add the current message
        messages.append({"role": "user", "content": message})
        
        try:
            response = self._call_claude_api(system_prompt, messages)
            
            # Parse the response, expecting JSON
            try:
                response_content = response.get("content", [])[0].get("text", "")
                
                # Detailed logging to debug JSON issues
                logger.info(f"Raw response content from Claude: {response_content[:500]}")
                
                # Strip any leading/trailing whitespace, markdown code blocks, etc.
                clean_content = response_content.strip()
                if clean_content.startswith("```json"):
                    # Handle markdown code blocks
                    end_marker = "```"
                    if end_marker in clean_content:
                        clean_content = clean_content[7:clean_content.rindex(end_marker)].strip()
                
                # Try to parse the JSON
                parsed_response = json.loads(clean_content)
                
                # Add debug log
                logger.info(f"Successfully parsed Claude response JSON: {json.dumps(parsed_response)[:200]}")
                
                # Make sure we have a proper message field
                if isinstance(parsed_response, dict) and 'message' in parsed_response:
                    return parsed_response
                else:
                    # Something went wrong - return a structured response with the content
                    logger.warning(f"Claude returned JSON without a message field: {parsed_response}")
                    return {
                        "message": clean_content,  # Use the raw content as the message
                        "extracted_info": {}
                    }
            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"Failed to parse Claude response: {str(e)}")
                logger.error(f"Problematic content: {response_content[:200]}")
                
                # Try to extract the direct text response from Claude when JSON parsing fails
                try:
                    if response and response.get("content") and len(response.get("content", [])) > 0:
                        direct_content = response.get("content", [])[0].get("text", "")
                        if direct_content:
                            # If we got a direct text response from Claude, use it
                            return {
                                "message": direct_content,
                                "extracted_info": {}
                            }
                except Exception as nested_error:
                    logger.error(f"Error extracting direct content: {str(nested_error)}")
                
                # Only if we can't get any usable content from Claude's response
                raise Exception(f"Failed to parse Claude response: {str(e)}")
                
        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}")
            return {
                "message": "I'm currently unable to process your information through my language system, but I'm still here to help. Could you tell me a bit more about what kind of activity you're interested in planning?",
                "extracted_info": {}
            }
    
    def process_participant_input(self, message, conversation_history=None, activity_info=None):
        """Process natural language input from a participant.
        
        Args:
            message (str): The message from the participant.
            conversation_history (list, optional): Previous messages in the conversation.
            activity_info (dict, optional): Information about the activity.
            
        Returns:
            dict: Claude's response with extracted preferences.
        """
        # Check if we need to use mock mode
        if hasattr(self, 'mock_mode') and self.mock_mode:
            return self._mock_participant_response(message)
            
        # Construct the prompt with system instructions
        system_prompt = """
        You are an AI-powered Activity Planner that helps participants share their preferences for a group activity.
        
        Your role is to extract structured preferences from their messages and respond in a helpful, conversational manner.
        Listen carefully to their specific preferences and acknowledge the details they provide in your response.
        Never respond with a generic greeting if the user has provided preference details.
        
        Format your response as JSON with the following structure:
        {
            "message": "Your natural language response to the user that specifically references details they provided",
            "extracted_preferences": {
                "activity": {
                    "activity_type": "Specific type of activity they prefer (e.g., hiking, movie, dinner) or null",
                    "physical_exertion": "Preferred activity level (low, moderate, high) or null",
                    "budget_range": "Budget preference with dollar amount if mentioned or null",
                    "learning_preference": "Whether they want to learn something new or practice existing skills or null"
                },
                "timing": {
                    "preferred_day": "Specific day(s) mentioned or category (weekday, weekend) or null",
                    "preferred_time": "Specific time or period (morning, afternoon, evening) or null",
                    "duration": "How long they want the activity to be (hours) or null",
                    "specific_date": "Any specific date mentioned or null"
                },
                "meals": {
                    "meals_included": "Whether they want meals included (can be array of meal types) or null",
                    "dietary_restrictions": "Any dietary restrictions mentioned or null",
                    "cuisine_preference": "Any preferred cuisine types or null"
                },
                "group": {
                    "has_children": "Whether children will participate (true/false) or null",
                    "has_seniors": "Whether seniors/elderly will participate (true/false) or null",
                    "group_size": "Preferred group size or null",
                    "social_level": "How social they want the activity to be or null"
                },
                "location": {
                    "indoor_outdoor": "Whether they prefer indoor or outdoor activities or null",
                    "specific_location": "Any specific venue or location mentioned or null",
                    "distance": "How far they're willing to travel or null",
                    "transportation": "Transportation preferences or requirements or null"
                },
                "requirements": {
                    "accessibility_needs": "Any accessibility requirements mentioned or null",
                    "special_interests": "Any special interests mentioned or null",
                    "additional_info": "Any other important preferences or null"
                }
            }
        }
        """
        
        if activity_info:
            system_prompt += f"""
            
            This is for the following activity:
            {activity_info.get('title', 'Group Activity')}
            {activity_info.get('description', '')}
            """
        
        # Convert conversation history to Claude's format
        messages = []
        if conversation_history:
            for msg in conversation_history:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})
        
        # Add the current message
        messages.append({"role": "user", "content": message})
        
        try:
            response = self._call_claude_api(system_prompt, messages)
            
            # Parse the response, expecting JSON
            try:
                response_content = response.get("content", [])[0].get("text", "")
                parsed_response = json.loads(response_content)
                return parsed_response
            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"Failed to parse Claude response: {str(e)}")
                # Fallback response
                return {
                    "message": "Thanks for sharing your preferences. Could you tell me more about what types of activities you enjoy most?",
                    "extracted_preferences": {}
                }
                
        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}")
            return {
                "message": "I appreciate you sharing your preferences. To create the best possible plan, could you tell me more about your favorite activities or any specific requirements you have?",
                "extracted_preferences": {}
            }
    
    def generate_activity_plan(self, activity_id, preferences):
        """Generate an activity plan using Claude.
        
        Args:
            activity_id (str): The activity ID.
            preferences (dict): Collected preferences from all participants.
            
        Returns:
            dict: Claude's generated plan.
        """
        # Check if we need to use mock mode
        if hasattr(self, 'mock_mode') and self.mock_mode:
            return self._mock_generate_plan(preferences)
        
        # Construct the prompt with system instructions
        system_prompt = """
        You are an AI-powered Activity Planner that generates detailed activity plans based on participants' preferences.
        
        Your task is to analyze all participants' preferences and create a comprehensive plan that best accommodates everyone.
        Pay special attention to:
        - Group composition (children, elderly, group size)
        - Activity preferences and physical exertion levels
        - Location preferences and transportation needs
        - Budget constraints
        - Timing preferences
        - Meal requirements and dietary restrictions
        - Special requirements and accessibility needs
        
        Format your response as JSON with the following structure:
        {
            "title": "Catchy, descriptive title for the activity that mentions the main activity type",
            "description": "Detailed description of the activity plan (at least 3-4 paragraphs) that explains:
            - The main activity and what participants will do
            - Why this activity is suitable for this specific group
            - How various preferences and requirements are accommodated
            - What makes this plan special or enjoyable",
            "schedule": [
                {"time": "Start time (format like 9:00 AM)", "activity": "Detailed description of this part of the activity (at least 1-2 sentences)"},
                {"time": "Next time", "activity": "Description of the next activity part"}
            ],
            "considerations": "List of important special considerations like accessibility accommodations, backup plans for weather, etc.",
            "alternatives": ["Fully described alternative activity 1", "Fully described alternative activity 2"]
        }
        """
        
        # Format preferences as a readable message
        message = f"I need to create an activity plan for a group with ID {activity_id}. Here are the collected preferences from all participants:\n\n"
        
        for participant_id, p_prefs in preferences.items():
            message += f"Participant {participant_id}:\n"
            for category, items in p_prefs.items():
                message += f"- {category.capitalize()}:\n"
                for key, value in items.items():
                    message += f"  - {key.replace('_', ' ').capitalize()}: {value}\n"
            message += "\n"
        
        message += "Please generate a detailed activity plan that accommodates these preferences as best as possible."
        
        try:
            response = self._call_claude_api(system_prompt, [{"role": "user", "content": message}])
            
            # Parse the response, expecting JSON
            try:
                response_content = response.get("content", [])[0].get("text", "")
                parsed_response = json.loads(response_content)
                return parsed_response
            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"Failed to parse Claude response: {str(e)}")
                # Fallback response
                return {
                    "error": "Failed to generate activity plan",
                    "raw_response": response.get("content", [])
                }
                
        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}")
            return {
                "error": f"API call failed: {str(e)}"
            }
    
    def _call_claude_api(self, system_prompt, messages):
        """Call the Claude API with the given prompt and messages.
        
        Args:
            system_prompt (str): The system prompt with instructions.
            messages (list): List of message objects.
            
        Returns:
            dict: The API response.
        """
        from flask import current_app
        import traceback
        
        # This is the most direct way to use the key - hardcode it in this function for testing
        # IMPORTANT: Remove this in production, only for troubleshooting
        direct_key = os.environ.get('ANTHROPIC_API_KEY')
        
        # Check for API key - first look at instance attribute, then try app config
        api_key = self.api_key
        
        current_app.logger.info(f"API key from self.api_key: {'Available' if api_key else 'Not available'}")
        
        if not api_key and current_app:
            api_key = current_app.config.get('ANTHROPIC_API_KEY')
            current_app.logger.info(f"API key from config: {'Available' if api_key else 'Not available'}")
            
        if not api_key:
            # Try to reload from environment as a last resort
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            current_app.logger.info(f"API key from environment: {'Available' if api_key else 'Not available'}")
            
        # Last resort - use the hardcoded key for this test
        if not api_key:
            current_app.logger.warning("Using hardcoded API key for testing - REMOVE THIS IN PRODUCTION")
            api_key = direct_key
            
        if not api_key:
            current_app.logger.error("ANTHROPIC_API_KEY not set in environment or app config")
            raise ValueError("ANTHROPIC_API_KEY not set. Please set this environment variable to use Claude.")
        
        # Check for model name - first look at instance attribute, then try app config
        model = self.model
        if not model and current_app:
            model = current_app.config.get('CLAUDE_MODEL', 'claude-3-opus-20240229')
        
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": 1000
        }
        
        current_app.logger.info(f"Calling Claude API with model: {model}")
        current_app.logger.info(f"API URL: {self.api_url}")
        current_app.logger.info(f"Using API key starting with: {api_key[:5]}...")
        current_app.logger.info(f"API Request headers: {headers}")
        current_app.logger.info(f"API Request body: {json.dumps(data)[:500]}...")
        
        try:
            current_app.logger.info("Sending request to Claude API...")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30  # 30 second timeout
            )
            
            current_app.logger.info(f"Claude API response status: {response.status_code}")
            
            if response.status_code != 200:
                current_app.logger.error(f"Claude API request failed with status {response.status_code}: {response.text}")
                raise Exception(f"API request failed with status {response.status_code}: {response.text}")
            
            response_data = response.json()
            current_app.logger.info(f"Claude API response: {json.dumps(response_data)[:500]}...")
            
            return response_data
            
        except Exception as e:
            current_app.logger.error(f"Error calling Claude API: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            raise
            
    # Mock response generators for when API key is not available
    def _mock_creator_response(self, message):
        """Generate a mock response for the creator input."""
        message = message.lower()
        
        if "museum" in message:
            return {
                "message": "A museum trip sounds great! I see you're interested in visiting a museum in New York City. I'd be happy to help plan this activity for your group that includes elderly members and children. A limo bus is a comfortable option for transportation, and stopping for a meal in the city will make it a complete experience.",
                "extracted_info": {
                    "activity_type": "Museum Visit",
                    "group_size": "16",
                    "group_composition": "10 adults including 2 elderly grandparents, 6 children ages 8-10",
                    "location": "New York City Museum",
                    "transportation": "Limo bus",
                    "timing": "6-hour trip, 10:00 AM to 5:00 PM",
                    "special_requirements": "Include a stop for sightseeing and a meal"
                }
            }
        elif "outdoor" in message or "hike" in message or "park" in message:
            return {
                "message": "An outdoor activity sounds perfect! I'd love to help you plan something that everyone can enjoy. Could you share more about how many people will be participating and if there are any specific outdoor activities your group prefers?",
                "extracted_info": {
                    "activity_type": "Outdoor Activity",
                    "group_size": None,
                    "location": "Outdoor",
                    "special_requirements": None
                }
            }
        else:
            return {
                "message": "Thanks for sharing your ideas! To help create the perfect activity plan, could you tell me more about your group size, general location, and any specific activities they might enjoy?",
                "extracted_info": {}
            }

    def _mock_participant_response(self, message):
        """Generate a mock response for participant input."""
        message = message.lower()
        
        if "outdoor" in message:
            return {
                "message": "I see you enjoy outdoor activities! That's great to know. Is there a particular type of outdoor activity you prefer, like hiking, parks, or water activities?",
                "extracted_preferences": {
                    "activity": {
                        "activity_type": "Outdoor"
                    },
                    "location": {
                        "indoor_outdoor": "outdoor"
                    }
                }
            }
        elif "weekend" in message:
            return {
                "message": "Weekend activities work well for you - noted! Do you have a preference for morning, afternoon, or evening activities on the weekend?",
                "extracted_preferences": {
                    "timing": {
                        "preferred_day": "Weekend"
                    }
                }
            }
        else:
            return {
                "message": "Thank you for sharing your preferences. This helps us plan an activity that everyone will enjoy. Is there anything specific you're looking forward to in this group activity?",
                "extracted_preferences": {}
            }
            
    def _mock_generate_plan(self, preferences):
        """Generate a mock plan."""
        # Create a basic plan
        return {
            "title": "Group Museum Trip with Lunch in New York City",
            "description": "A day trip to the Museum of Natural History in New York City, perfect for families with children and seniors. The group will travel together by chartered bus, enjoying comfortable transportation without the hassle of driving or parking in the city.\n\nThe museum offers something for everyone - from dinosaur exhibits that will captivate the children to art and cultural displays that adults and seniors will appreciate. The layout is wheelchair accessible with plenty of seating throughout for those who need rest breaks.\n\nAfter exploring the museum, the group will enjoy lunch at a family-friendly restaurant nearby that accommodates various dietary needs. The return trip will include a brief sightseeing drive through Central Park before heading home.",
            "schedule": [
                {"time": "9:30 AM", "activity": "Meet at designated parking area in Belmar for departure"},
                {"time": "10:00 AM", "activity": "Depart Belmar in chartered limo bus"},
                {"time": "11:15 AM", "activity": "Brief sightseeing stop at a scenic viewpoint"},
                {"time": "12:00 PM", "activity": "Arrive at Museum of Natural History"},
                {"time": "2:30 PM", "activity": "Lunch at family-friendly restaurant near museum"},
                {"time": "3:45 PM", "activity": "Brief Central Park sightseeing drive"},
                {"time": "4:15 PM", "activity": "Begin return journey to Belmar"},
                {"time": "5:30 PM", "activity": "Arrive back at starting point in Belmar"}
            ],
            "considerations": "The museum has wheelchair accessibility for elderly members. The restaurant can accommodate common dietary restrictions with advance notice. The bus has restroom facilities and storage for personal items.",
            "alternatives": [
                "Metropolitan Museum of Art with lunch in the museum café",
                "Bronx Zoo visit with picnic lunch in designated areas"
            ]
        }
        
        
# Initialize the Claude service
claude_service = ClaudeService()