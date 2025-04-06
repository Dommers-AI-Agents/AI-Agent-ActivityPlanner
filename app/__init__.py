"""
Application factory for the Group Activity Planner AI Agent.
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('app.config.Config')
    
    # Override config if provided
    if config:
        app.config.update(config)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # Register blueprints
    from app.views.main import main_bp
    from app.views.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create database tables if needed (development only)
    if app.config['ENV'] == 'development':
        with app.app_context():
            db.create_all()
    
    return app
