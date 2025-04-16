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
        self.model = "claude-3-sonnet-20240229"  # Default model, can be configured
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the service with a Flask app."""
        self.app = app
        self.api_key = app.config.get('ANTHROPIC_API_KEY')
        self.model = app.config.get('CLAUDE_MODEL', self.model)
        
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set. Claude integration will not work.")
    
    def process_activity_creator_input(self, message, conversation_history=None):
        """Process natural language input from the activity creator.
        
        Args:
            message (str): The message from the activity creator.
            conversation_history (list, optional): Previous messages in the conversation.
            
        Returns:
            dict: Claude's response with extracted information.
        """
        # Construct the prompt with system instructions
        system_prompt = """
        You are an AI-powered Activity Planner that helps people plan group activities.
        
        Your role is to gather information about:
        1. What kind of activity they want to plan (e.g., dinner, movie, hiking, museum visit, etc.)
        2. Details about their group (size, age range, interests, relationships)
        3. Location preferences (indoor/outdoor, specific venues or cities)
        4. Budget constraints and considerations
        5. Special requirements (accessibility needs, dietary restrictions)
        6. Timing preferences (date, time of day, duration)
        7. Transportation needs or preferences
        
        Extract structured information from their messages and respond in a helpful, conversational manner.
        Always try to provide a thoughtful response that acknowledges the specific details they've provided.
        If they provide a lot of detailed information, respond conversationally to that information.
        Never respond with a generic greeting if the user has provided activity details.
        
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
                "special_requirements": "Any special requirements or considerations mentioned or null"
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
                parsed_response = json.loads(response_content)
                return parsed_response
            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"Failed to parse Claude response: {str(e)}")
                # Fallback response
                return {
                    "message": "I'm having trouble processing your input. Could you tell me more about the activity you'd like to plan?",
                    "extracted_info": {
                        "activity_type": None,
                        "group_info": None,
                        "special_considerations": None
                    }
                }
                
        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}")
            return {
                "message": "Sorry, I'm having trouble connecting to my language processing system. Could you try again?",
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
                    "message": "I'm having trouble understanding your preferences. Could you tell me more about what kinds of activities you enjoy?",
                    "extracted_preferences": {}
                }
                
        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}")
            return {
                "message": "Sorry, I'm having trouble connecting to my language processing system. Could you try again?",
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
        
        # Check for API key - first look at instance attribute, then try app config
        api_key = self.api_key
        if not api_key and current_app:
            api_key = current_app.config.get('ANTHROPIC_API_KEY')
            
        if not api_key:
            current_app.logger.error("ANTHROPIC_API_KEY not set in environment or app config")
            raise ValueError("ANTHROPIC_API_KEY not set. Please set this environment variable to use Claude.")
        
        # Check for model name - first look at instance attribute, then try app config
        model = self.model
        if not model and current_app:
            model = current_app.config.get('CLAUDE_MODEL', 'claude-3-sonnet-20240229')
        
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
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                current_app.logger.error(f"Claude API request failed with status {response.status_code}: {response.text}")
                raise Exception(f"API request failed with status {response.status_code}: {response.text}")
            
            return response.json()
            
        except Exception as e:
            current_app.logger.error(f"Error calling Claude API: {str(e)}")
            raise

# Initialize the Claude service
claude_service = ClaudeService()
