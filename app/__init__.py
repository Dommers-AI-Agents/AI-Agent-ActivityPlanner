"""
Application factory for the Group Activity Planner AI Agent.
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_login import LoginManager
import logging
from logging.handlers import RotatingFileHandler

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('app.config.Config')

    # Setup logging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('AI Group Planner startup')
    
    # Override config if provided
    if config:
        app.config.update(config)
    
    #print config key for email test
    print("TWILIO_ACCOUNT_SID:", os.environ.get('TWILIO_ACCOUNT_SID', 'Not set'))
    print("TWILIO_PHONE_NUMBER:", os.environ.get('TWILIO_PHONE_NUMBER', 'Not set'))
    print("TWILIO_AUTH_TOKEN:", "***" if os.environ.get('TWILIO_AUTH_TOKEN') else 'Not set')
    print("SENDGRID_API_KEY:", "***" if os.environ.get('SENDGRID_API_KEY') else 'Not set')

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    CORS(app)

     # Initialize SMS and Email services
    from app.services.sms_service import sms_service
    from app.services.email_service import email_service
    sms_service.init_app(app)
    email_service.init_app(app)

    # Initialize Claude services
    from app.services.claude_service import claude_service
    claude_service.init_app(app)
    
    # Log Claude API key status
    if app.config.get('ANTHROPIC_API_KEY'):
        app.logger.info(f"Claude service initialized with API key: {app.config.get('ANTHROPIC_API_KEY')[:5]}...")
    else:
        app.logger.warning("No ANTHROPIC_API_KEY found in config. Claude API will not work correctly.")
        # For testing purposes only - set a dummy key
        app.config['ANTHROPIC_API_KEY'] = "dummy-key-for-testing"
        app.logger.warning("Set dummy API key for testing. Real Claude API calls will fail.")

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.database import User  # Add this import inside the function
        return User.query.get(user_id)
    
    # Register blueprints
    from app.views.main import main_bp
    from app.views.api import api_bp
    from app.views.auth import auth_bp
    from app.views.ai_nlp import ai_nlp_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp)
    app.register_blueprint(ai_nlp_bp, url_prefix='/api/ai')
    
    # Add custom Jinja2 filters
    from markupsafe import Markup, escape
    
    @app.template_filter('nl2br')
    def nl2br_filter(s):
        """Convert newlines to <br> tags for display in HTML."""
        if not s:
            return ""
        
        # Replace <br> and <br /> with newlines first, before escaping
        if isinstance(s, str):
            s = s.replace('<br>', '\n').replace('<br />', '\n').replace('<br/>', '\n')
        
        # Then escape and convert newlines to <br> tags
        return Markup(escape(s).replace('\n', '<br>\n'))

    # Create database tables if needed (development only)
    if app.config['ENV'] == 'development':
        with app.app_context():
            db.create_all()
    
    return app
