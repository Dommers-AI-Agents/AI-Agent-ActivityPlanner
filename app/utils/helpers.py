"""
Helper utilities for the Group Activity Planner.
"""
import re
import os
import json
from datetime import datetime, date
from flask import current_app

def format_phone_number(phone_number):
    """Format a phone number for display.
    
    Args:
        phone_number (str): The phone number to format.
    
    Returns:
        str: The formatted phone number.
    """
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone_number)
    
    # Format based on length
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone_number

def normalize_phone_number(phone_number):
    """Normalize a phone number to E.164 format.
    
    Args:
        phone_number (str): The phone number to normalize.
    
    Returns:
        str: The normalized phone number.
    """
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone_number)
    
    # Add country code if needed
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+{digits}"
    elif not phone_number.startswith('+'):
        return f"+{digits}"
    else:
        return phone_number

def format_datetime(dt):
    """Format a datetime for display.
    
    Args:
        dt (datetime): The datetime to format.
    
    Returns:
        str: The formatted datetime.
    """
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    
    if isinstance(dt, datetime):
        return dt.strftime('%B %d, %Y at %I:%M %p')
    elif isinstance(dt, date):
        return dt.strftime('%B %d, %Y')
    else:
        return str(dt)

def format_currency(amount):
    """Format a currency amount.
    
    Args:
        amount (float): The amount to format.
    
    Returns:
        str: The formatted amount.
    """
    if amount is None:
        return '$0.00'
    
    return '${:,.2f}'.format(float(amount))

def log_error(message, error=None):
    """Log an error message.
    
    Args:
        message (str): The error message.
        error (Exception, optional): The exception. Defaults to None.
    """
    if error:
        current_app.logger.error(f"{message}: {str(error)}")
    else:
        current_app.logger.error(message)

def log_info(message):
    """Log an info message.
    
    Args:
        message (str): The info message.
    """
    current_app.logger.info(message)

def get_app_url():
    """Get the application base URL.
    
    Returns:
        str: The application base URL.
    """
    return current_app.config.get('APP_URL', 'http://localhost:5000')

def truncate_text(text, max_length=100):
    """Truncate text to a maximum length.
    
    Args:
        text (str): The text to truncate.
        max_length (int, optional): The maximum length. Defaults to 100.
    
    Returns:
        str: The truncated text.
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + '...'

def to_json(data):
    """Convert data to JSON string.
    
    Args:
        data: The data to convert.
    
    Returns:
        str: The JSON string.
    """
    return json.dumps(data)

def from_json(json_str):
    """Convert JSON string to data.
    
    Args:
        json_str (str): The JSON string.
    
    Returns:
        The parsed data.
    """
    if not json_str:
        return None
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None
