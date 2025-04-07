"""
Database models for the Group Activity Planner AI Agent.
"""
from datetime import datetime, timedelta
import uuid
import json
import jwt
from flask import current_app
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())

class User(db.Model, UserMixin):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with activities
    activities = db.relationship('Activity', backref='creator', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_reset_token(self, expires_in=3600):
        """Generate a password reset token.
        
        Args:
            expires_in (int): Token expiration time in seconds. Default is 1 hour.
            
        Returns:
            str: JWT token for password reset
        """
        return jwt.encode(
            {
                'reset_password': self.id,
                'exp': datetime.utcnow() + timedelta(seconds=expires_in)
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    
    @staticmethod
    def verify_reset_token(token):
        """Verify a password reset token.
        
        Args:
            token (str): The token to verify
            
        Returns:
            User: The user if token is valid, None otherwise
        """
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            user_id = data.get('reset_password')
            if not user_id:
                return None
            return User.query.get(user_id)
        except Exception:
            return None
        
    def __repr__(self):
        return f'<User {self.username}>'

class Activity(db.Model):
    """Activity planning session model."""
    __tablename__ = 'activities'
    
    # In the Activity class
    creator_id = db.Column(db.String(36), db.ForeignKey('users.id', name='fk_activity_creator'), nullable=True)
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    title = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='planning', nullable=False)
    created_id = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    participants = db.relationship('Participant', back_populates='activity', cascade='all, delete-orphan')
    messages = db.relationship('Message', back_populates='activity', cascade='all, delete-orphan')
    preferences = db.relationship('Preference', back_populates='activity', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Activity {self.id}>'
    
    @property
    def is_complete(self):
        """Check if all participants have completed their inputs."""
        return all(p.status == 'complete' for p in self.participants)
    
    def to_dict(self):
        """Convert activity to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'participants': [p.to_dict() for p in self.participants],
            'preferences': [p.to_dict() for p in self.preferences],
        }

class Participant(db.Model):
    """Participant model."""
    __tablename__ = 'participants'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    activity_id = db.Column(db.String(36), db.ForeignKey('activities.id'), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    allow_group_text = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default='invited', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    activity = db.relationship('Activity', back_populates='participants')
    preferences = db.relationship('Preference', back_populates='participant', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Participant {self.name or self.phone_number}>'
    
    def to_dict(self):
        """Convert participant to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'phone_number': self.phone_number,
            'email': self.email,
            'allow_group_text': self.allow_group_text,
            'status': self.status,
            'preferences': [p.to_dict() for p in self.preferences],
        }

class Preference(db.Model):
    """Preference model for capturing participants' preferences."""
    __tablename__ = 'preferences'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    activity_id = db.Column(db.String(36), db.ForeignKey('activities.id'), nullable=False)
    participant_id = db.Column(db.String(36), db.ForeignKey('participants.id'), nullable=True)
    category = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    activity = db.relationship('Activity', back_populates='preferences')
    participant = db.relationship('Participant', back_populates='preferences')
    
    def __repr__(self):
        return f'<Preference {self.category}.{self.key}>'
    
    def to_dict(self):
        """Convert preference to dictionary."""
        # Try to parse JSON values
        try:
            parsed_value = json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            parsed_value = self.value
            
        return {
            'id': self.id,
            'category': self.category,
            'key': self.key,
            'value': parsed_value,
        }

class Message(db.Model):
    """Message model for communication history."""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    activity_id = db.Column(db.String(36), db.ForeignKey('activities.id'), nullable=False)
    participant_id = db.Column(db.String(36), db.ForeignKey('participants.id'), nullable=True)
    direction = db.Column(db.String(10), nullable=False)  # 'incoming' or 'outgoing'
    channel = db.Column(db.String(10), nullable=False)    # 'sms', 'email', 'web'
    content = db.Column(db.Text, nullable=False)
    meta_data = db.Column(db.Text, nullable=True)          # JSON string for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    activity = db.relationship('Activity', back_populates='messages')
    
    def __repr__(self):
        return f'<Message {self.id}>'
    
    @property
    def metadata_dict(self):
        """Get metadata as dictionary."""
        if not self.meta_data:
            return {}
        try:
            return json.loads(self.meta_data)
        except json.JSONDecodeError:
            return {}
    
    def to_dict(self):
        """Convert message to dictionary."""
        return {
            'id': self.id,
            'activity_id': self.activity_id,
            'participant_id': self.participant_id,
            'direction': self.direction,
            'channel': self.channel,
            'content': self.content,
            'metadata': self.metadata_dict,
            'created_at': self.created_at.isoformat(),
        }

class Plan(db.Model):
    """Generated plan model."""
    __tablename__ = 'plans'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    activity_id = db.Column(db.String(36), db.ForeignKey('activities.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    schedule = db.Column(db.Text, nullable=True)  # JSON string for schedule data
    status = db.Column(db.String(50), default='draft', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Plan {self.title}>'
    
    @property
    def schedule_dict(self):
        """Get schedule as dictionary."""
        if not self.schedule:
            return {}
        try:
            return json.loads(self.schedule)
        except json.JSONDecodeError:
            return {}
    
    def to_dict(self):
        """Convert plan to dictionary."""
        return {
            'id': self.id,
            'activity_id': self.activity_id,
            'title': self.title,
            'description': self.description,
            'schedule': self.schedule_dict,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
