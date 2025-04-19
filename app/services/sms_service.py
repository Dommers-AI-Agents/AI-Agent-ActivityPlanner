"""
SMS service for sending text messages via Twilio.
"""
import os
from flask import current_app
from twilio.rest import Client

class SMSService:
    """Service for sending SMS messages via Twilio."""
    
    def __init__(self, app=None):
        """Initialize the SMS service."""
        self.app = app
        self.client = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the service with a Flask app."""
        import logging
        logger = logging.getLogger(__name__)
        
        self.app = app
        logger.info("Initializing SMS service")
        
        # Initialize Twilio client
        account_sid = app.config.get('TWILIO_ACCOUNT_SID')
        auth_token = app.config.get('TWILIO_AUTH_TOKEN')
        phone_number = app.config.get('TWILIO_PHONE_NUMBER')
        
        # Log configuration status
        logger.info(f"Twilio configuration: ACCOUNT_SID={'CONFIGURED' if account_sid else 'MISSING'}, "
                   f"AUTH_TOKEN={'CONFIGURED' if auth_token else 'MISSING'}, "
                   f"PHONE_NUMBER={'CONFIGURED' if phone_number else 'MISSING'}")
        
        if account_sid and auth_token:
            try:
                self.client = Client(account_sid, auth_token)
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {str(e)}", exc_info=True)
                self.client = None
        else:
            logger.warning("Twilio client not initialized due to missing credentials")
            self.client = None
    
    def send_message(self, to_number, body, from_number=None):
        """Send an SMS message.
        
        Args:
            to_number (str): The recipient's phone number.
            body (str): The message body.
            from_number (str, optional): The sender's phone number. Defaults to the configured Twilio number.
        
        Returns:
            dict: Response data from Twilio.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Check if client is initialized
            if not self.client:
                if not self.app:
                    logger.error("SMS service not initialized with app")
                    raise RuntimeError("SMS service not initialized with app")
                
                # Try to initialize with app
                logger.info("Attempting to initialize SMS service")
                self.init_app(self.app)
            
            # Verify client initialization
            if not self.client:
                # Check if Twilio credentials are configured
                account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
                auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
                
                if not account_sid or not auth_token:
                    logger.error("Twilio credentials missing: ACCOUNT_SID=%s, AUTH_TOKEN=%s", 
                               "CONFIGURED" if account_sid else "MISSING",
                               "CONFIGURED" if auth_token else "MISSING")
                
                raise RuntimeError("Twilio client not initialized - check credentials")
            
            # Use configured Twilio number if not specified
            if not from_number:
                from_number = current_app.config.get('TWILIO_PHONE_NUMBER')
                if not from_number:
                    logger.error("TWILIO_PHONE_NUMBER not configured in app settings")
                    raise ValueError("No 'from' phone number specified and TWILIO_PHONE_NUMBER not configured")
            
            # Clean phone numbers to ensure they're in E.164 format
            to_number = self._clean_phone_number(to_number)
            
            # Log the SMS being sent
            logger.info(f"Sending SMS to {to_number} from {from_number}")
            
            # Send message
            message = self.client.messages.create(
                to=to_number,
                from_=from_number,
                body=body
            )
            
            # Log success
            logger.info(f"SMS sent successfully: SID={message.sid}, Status={message.status}")
            
            return {
                'sid': message.sid,
                'status': message.status,
                'to': message.to,
                'body': message.body
            }
        
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {str(e)}", exc_info=True)
            raise
    
    def send_welcome_message(self, to_number, activity_id, participant_id=None):
        """Send a welcome message with a link to the web application.
        
        Args:
            to_number (str): The recipient's phone number.
            activity_id (str): The activity ID.
            participant_id (str, optional): The participant ID if known.
        
        Returns:
            dict: Response data from Twilio.
        """
        # Build the web URL
        app_url = current_app.config.get('APP_URL', 'https://localhost:5000')
        
        if participant_id:
            url = f"{app_url}/activity/{activity_id}?participant={participant_id}"
        else:
            url = f"{app_url}/activity/{activity_id}"
        
        # Short message body
        body = (
            "Help Wesley plan your group activity. \n\n"
            "Click here: " f"{url}"
        )

        # Original message body    
        #body = (
         #   "Welcome to the Wesley's Group Activity Planner! 🎉\n\n"
          #  "Help plan the perfect activity by sharing your preferences. "
           # "Click the link below to continue:\n\n"
           # f"{url}\n\n"
           # "This link is unique to you. No need to create an account!"
        #)
        
        return self.send_message(to_number, body)
    
    def send_notification(self, to_number, message, activity_id=None):
        """Send a notification message.
        
        Args:
            to_number (str): The recipient's phone number.
            message (str): The notification message.
            activity_id (str, optional): The activity ID to include in the message.
        
        Returns:
            dict: Response data from Twilio.
        """
        body = message
        
        if activity_id:
            app_url = current_app.config.get('APP_URL', 'https://localhost:5000')
            url = f"{app_url}/activity/{activity_id}"
            body += f"\n\nView details: {url}"
        
        return self.send_message(to_number, body)
    
    def send_plan_notification(self, to_number, activity_id, plan=None):
        """Send a notification that a plan has been created.
        
        Args:
            to_number (str): The recipient's phone number.
            activity_id (str): The activity ID.
            plan (dict, optional): The plan details.
        
        Returns:
            dict: Response data from Twilio.
        """
        app_url = current_app.config.get('APP_URL', 'https://localhost:5000')
        url = f"{app_url}/activity/{activity_id}/plan"
        
        if plan:
            body = (
                f"Your group activity plan is ready! 📅\n\n"
                f"Activity: {plan.get('title', 'Group Activity')}\n"
                f"Click here to view and provide feedback: {url}"
            )
        else:
            body = (
                "Your group activity plan is ready! 📅\n\n"
                f"Click here to view and provide feedback: {url}"
            )
        
        return self.send_message(to_number, body)
    
    def handle_incoming_message(self, from_number, body):
        """Handle an incoming SMS message.
        
        Args:
            from_number (str): The sender's phone number.
            body (str): The message body.
        
        Returns:
            str: The response message to send back.
        """
        # In a real implementation, this would process the incoming message
        # and route it to the appropriate handler
        
        # For this example, we'll just acknowledge and direct to the web interface
        app_url = current_app.config.get('APP_URL', 'https://localhost:5000')
        
        return (
            "Thanks for your message! For the best experience, please use our web interface. "
            f"Visit {app_url} to continue planning your activity."
        )
    
    def _clean_phone_number(self, number):
        """Ensure the phone number is in E.164 format.
        
        Args:
            number (str): The phone number to clean.
        
        Returns:
            str: The cleaned phone number.
        """
        # Simple cleaning for demonstration
        # In a real application, you'd want more robust phone number validation and formatting
        number = number.strip()
        
        # Add '+1' for US numbers that don't have it
        if number.startswith('1') and not number.startswith('+1'):
            number = '+' + number
        elif not number.startswith('+'):
            if number.startswith('1'):
                number = '+' + number
            else:
                number = '+1' + number
        
        return number

# Initialize the SMS service
sms_service = SMSService()
