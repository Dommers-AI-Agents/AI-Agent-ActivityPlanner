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
        1. What kind of activity they want to plan
        2. Details about their group (size, age range, interests)
        3. Any special requirements or considerations
        
        Extract structured information from their messages and respond in a helpful, conversational manner.
        
        Format your response as JSON with the following structure:
        {
            "message": "Your natural language response to the user",
            "extracted_info": {
                "activity_type": "The type of activity mentioned or null",
                "group_info": "Information about the group or null",
                "special_considerations": "Any special requirements or null"
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
        
        Format your response as JSON with the following structure:
        {
            "message": "Your natural language response to the user",
            "extracted_preferences": {
                "activity": {
                    "activity_type": "Type of activity they prefer or null",
                    "physical_exertion": "Preferred activity level or null",
                    "budget_range": "Budget preference or null"
                },
                "timing": {
                    "preferred_day": "Preferred day or null",
                    "preferred_time": "Preferred time or null",
                    "duration": "Preferred duration or null"
                },
                "meals": {
                    "meals_included": "Whether they want meals or null",
                    "dietary_restrictions": "Dietary restrictions or null"
                },
                "requirements": {
                    "accessibility_needs": "Accessibility requirements or null",
                    "additional_info": "Any other preferences or null"
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
        
        Your task is to analyze all participants' preferences and create a plan that best accommodates everyone.
        
        Format your response as JSON with the following structure:
        {
            "title": "Catchy title for the activity",
            "description": "Detailed description of the activity plan",
            "schedule": [
                {"time": "Start time", "activity": "Description of this part of the activity"},
                {"time": "Next time", "activity": "Description of the next part"}
            ],
            "considerations": "Special considerations for this plan",
            "alternatives": ["Alternative activity 1", "Alternative activity 2"]
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
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": self.model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": 1000
        }
        
        response = requests.post(
            self.api_url,
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")
        
        return response.json()

# Initialize the Claude service
claude_service = ClaudeService()
