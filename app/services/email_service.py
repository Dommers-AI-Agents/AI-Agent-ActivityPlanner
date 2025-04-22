"""
Email service for sending emails via SendGrid.
"""
import os
from flask import current_app, render_template
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition

class EmailService:
    """Service for sending emails via SendGrid."""
    
    def __init__(self, app=None):
        """Initialize the email service."""
        self.app = app
        self.client = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the service with a Flask app."""
        self.app = app
        
        # Initialize SendGrid client
        api_key = app.config.get('SENDGRID_API_KEY')
        print("🔍 SENDGRID_API_KEY inside EmailService.init_app:", api_key)
        
        if api_key:
            self.client = SendGridAPIClient(api_key)
            print("✅ SendGrid client initialized!")
        else:
            print("❌ No SENDGRID_API_KEY found. EmailService not initialized.")
    
    def send_email(self, to_email, subject, html_content, from_email=None):
        """Send an email.
        
        Args:
            to_email (str): The recipient's email address.
            subject (str): The email subject.
            html_content (str): The HTML content of the email.
            from_email (str, optional): The sender's email address. Defaults to the configured default.
        
        Returns:
            dict: Response data from SendGrid.
        """
        if not self.client:
            if not self.app:
                raise RuntimeError("Email service not initialized with app")
            self.init_app(self.app)
        
        if not self.client:
            raise RuntimeError("SendGrid client not initialized")
        
        # Use configured default sender if not specified
        if not from_email:
            from_email = current_app.config.get('DEFAULT_FROM_EMAIL')
            if not from_email:
                raise ValueError("No 'from' email specified and DEFAULT_FROM_EMAIL not configured")
        
        # Create the email
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        try:
            response = self.client.send(message)
            return {
                'status_code': response.status_code,
                'body': response.body,
                'headers': response.headers
            }
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {str(e)}")
            return {
                'error': str(e)
            }
    
    def send_welcome_email(self, to_email, participant_name, activity_id, participant_id):
        """Send a welcome email with a link to the web application.
        
        Args:
            to_email (str): The recipient's email address.
            participant_name (str): The participant's name.
            activity_id (str): The activity ID.
            participant_id (str): The participant ID.
        
        Returns:
            dict: Response data from SendGrid.
        """
        # Build the web URL
        app_url = current_app.config.get('APP_URL', 'https://localhost:5000')
        url = f"{app_url}/activity/{activity_id}?participant={participant_id}"
        
        # Define email subject
        subject = "Welcome to Group Activity Planner!"
        
        # Create email content
        html_content = render_template(
            'emails/welcome.html',
            participant_name=participant_name,
            activity_url=url
        )
        
        return self.send_email(to_email, subject, html_content)
    
    def send_plan_email(self, to_email, participant_name, activity_id, plan, is_final=False):
        """Send an email with the activity plan.
        
        Args:
            to_email (str): The recipient's email address.
            participant_name (str): The participant's name.
            activity_id (str): The activity ID.
            plan (dict): The plan details.
            is_final (bool, optional): Whether this is the final plan. Defaults to False.
        
        Returns:
            dict: Response data from SendGrid.
        """
        # Build the web URL
        app_url = current_app.config.get('APP_URL', 'https://localhost:5000')
        url = f"{app_url}/activity/{activity_id}/plan"
        
        # Define email subject
        subject = f"Your Group Activity Plan: {plan.get('title', 'Activity Plan')}"
        if is_final:
            subject = f"FINAL: {subject}"
        
        # Create email content
        html_content = render_template(
            'emails/plan.html',
            participant_name=participant_name,
            plan=plan,
            plan_url=url,
            is_final=is_final
        )
        
        return self.send_email(to_email, subject, html_content)
    
    def send_feedback_request(self, to_email, participant_name, activity_id, plan):
        """Send an email requesting feedback on the plan.
        
        Args:
            to_email (str): The recipient's email address.
            participant_name (str): The participant's name.
            activity_id (str): The activity ID.
            plan (dict): The plan details.
        
        Returns:
            dict: Response data from SendGrid.
        """
        # Build the web URL
        app_url = current_app.config.get('APP_URL', 'https://localhost:5000')
        url = f"{app_url}/activity/{activity_id}/feedback"
        
        # Define email subject
        subject = f"We'd Like Your Feedback on the Group Activity Plan"
        
        # Create email content
        html_content = render_template(
            'emails/feedback.html',
            participant_name=participant_name,
            plan_title=plan.get('title', 'Activity Plan'),
            feedback_url=url
        )
        
        return self.send_email(to_email, subject, html_content)
    
    def send_notification_email(self, to_email, participant_name, subject, message, activity_id=None):
        """Send a notification email.
        
        Args:
            to_email (str): The recipient's email address.
            participant_name (str): The participant's name.
            subject (str): The email subject.
            message (str): The notification message.
            activity_id (str, optional): The activity ID. Defaults to None.
        
        Returns:
            dict: Response data from SendGrid.
        """
        # Build the web URL if activity_id is provided
        activity_url = None
        if activity_id:
            app_url = current_app.config.get('APP_URL', 'https://localhost:5000')
            activity_url = f"{app_url}/activity/{activity_id}"
        
        # Create email content
        html_content = render_template(
            'emails/notification.html',
            participant_name=participant_name,
            message=message,
            activity_url=activity_url
        )
        
        return self.send_email(to_email, subject, html_content)
    
    def send_group_notification(self, to_emails, subject, message, activity_id=None):
        """Send a notification to multiple participants.
        
        Args:
            to_emails (list): List of recipient email addresses.
            subject (str): The email subject.
            message (str): The notification message.
            activity_id (str, optional): The activity ID to include in the email.
        
        Returns:
            list: List of response data from SendGrid for each recipient.
        """
        responses = []
        
        # Build the web URL if activity_id is provided
        app_url = None
        if activity_id:
            app_url = current_app.config.get('APP_URL', 'https://localhost:5000')
            url = f"{app_url}/activity/{activity_id}"
        
        # Create email content
        html_content = render_template(
            'emails/notification.html',
            message=message,
            activity_url=url if app_url else None
        )
        
        # Send to each recipient individually
        for email in to_emails:
            response = self.send_email(email, subject, html_content)
            responses.append(response)
        
        return responses
        
    def send_password_reset_email(self, user, token):
        """Send a password reset email with a reset link.
        
        Args:
            user (User): The user requesting the password reset.
            token (str): The password reset token.
            
        Returns:
            dict: Response data from SendGrid.
        """
        # Build the reset URL
        app_url = current_app.config.get('APP_URL', 'https://localhost:5000')
        reset_url = f"{app_url}/auth/reset_password/{token}"
        
        # Define email subject
        subject = "Password Reset Request"
        
        # Try to use the template if it exists
        try:
            html_content = render_template(
                'emails/password_reset.html',
                user=user,
                reset_url=reset_url
            )
        except Exception:
            # Fallback to inline template if the file doesn't exist
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Password Reset Request</h2>
                <p>Hello {user.name or user.email},</p>
                <p>You requested a password reset for your account. Please click the link below to reset your password:</p>
                <p style="margin: 20px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #4CAF50; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px;">
                        Reset Your Password
                    </a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all;">{reset_url}</p>
                <p>If you did not request a password reset, please ignore this email. Your password will remain unchanged.</p>
                <p>This link will expire in 1 hour.</p>
            </div>
            """
        
        return self.send_email(user.email, subject, html_content)

# Initialize the email service
email_service = EmailService()
