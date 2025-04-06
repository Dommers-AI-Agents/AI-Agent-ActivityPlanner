"""
Application factory for the Group Activity Planner AI Agent.
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_login import LoginManager

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

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    # Register blueprints
    from app.views.main import main_bp
    from app.views.api import api_bp
    from app.views.auth import auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp)
    
    # Create database tables if needed (development only)
    if app.config['ENV'] == 'development':
        with app.app_context():
            db.create_all()
    
    return app
