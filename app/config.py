"""
Configuration settings for the Group Activity Planner AI Agent.
"""
import os
from datetime import timedelta

class Config:
    """Base configuration."""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-for-development-only')
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')
    
    # SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Claude settings
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-3-sonnet-20240229')
    
    # Twilio settings
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    
    # SendGrid settings
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')
    
    # AI Agent settings
    MAX_QUESTIONS_PER_BATCH = 5
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    ENV = 'development'

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    ENV = 'production'
    
    # In production, ensure SECRET_KEY is set
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Use secure cookies in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

# Select the appropriate configuration based on environment
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

# Default to development config
Config = config_by_name.get(os.environ.get('FLASK_ENV', 'development'), DevelopmentConfig)
