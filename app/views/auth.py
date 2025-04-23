from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
import json
import uuid
import requests
from urllib.parse import urlencode
#from werkzeug.urls import url_parse as werkzeug_url_parse
from app import db
from app.models.database import User
from app.services.email_service import email_service

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Capture next URL right away so we don't lose it
    next_page = request.args.get('next')
    
    if current_user.is_authenticated:
        # If already logged in, redirect to the appropriate page
        if next_page and not next_page.startswith('//') and ':' not in next_page:
            return redirect(next_page)
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember_me = 'remember_me' in request.form
        
        # Get the next URL from the hidden field or the query parameter
        next_page = request.form.get('next_url') or next_page
        
        user = User.query.filter_by(email=email).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login', next=next_page))
            
        login_user(user, remember=remember_me)
        
        # Safety check on the next URL
        if not next_page or next_page.startswith('//') or ':' in next_page:
            next_page = url_for('main.index')
            
        # Mark the login as successful and restore activity data if needed
        if 'create-activity' in next_page:
            session['login_successful'] = True
            session['restore_activity_data'] = True
            current_app.logger.info("Setting restore_activity_data flag for user after login")
            
        return redirect(next_page)
    
    # Pass the redirect URL if it exists
    return render_template('auth/login.html', redirect_url=next_page)

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Capture next URL right away so we don't lose it
    next_page = request.args.get('next')
    
    if current_user.is_authenticated:
        # If already logged in, redirect to the appropriate page
        if next_page and not next_page.startswith('//') and ':' not in next_page:
            return redirect(next_page)
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        # Get the next URL from the hidden field or the query parameter
        next_page = request.form.get('next_url') or next_page
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register', next=next_page))
            
        user = User(email=email, name=name)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Auto-login after registration
        login_user(user)
        
        # Safety check on the next URL
        if not next_page or next_page.startswith('//') or ':' in next_page:
            next_page = url_for('main.index')
        
        # If we have a "create-activity" next page, mark login as successful
        if 'create-activity' in next_page:
            session['login_successful'] = True
            session['restore_activity_data'] = True
            current_app.logger.info("Setting restore_activity_data flag for user after registration")
            flash('Registration successful! Continuing with your activity...', 'success')
            return redirect(next_page)
        
        # Default redirect
        flash('Registration successful! You are now logged in.', 'success')
        return redirect(url_for('main.index'))
        
    # Pass the redirect URL if it exists
    return render_template('auth/register.html', redirect_url=next_page)

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.get_reset_token()
            email_service.send_password_reset_email(user, token)
            flash('Check your email for instructions to reset your password', 'info')
        else:
            flash('Email not found. Please check your email or register for an account.', 'error')
            return redirect(url_for('auth.register'))
            
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password_request.html')

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired reset token. Please try again.', 'error')
        return redirect(url_for('auth.reset_password_request'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        password2 = request.form.get('password2')
        
        if password != password2:
            flash('Passwords do not match. Please try again.', 'error')
            return render_template('auth/reset_password.html', token=token)
            
        user.set_password(password)
        db.session.commit()
        flash('Your password has been reset. You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html', token=token)

# OAuth Authentication Routes

@auth_bp.route('/google-login')
def google_login():
    """Initiate Google OAuth login flow."""
    # Google OAuth configuration
    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    redirect_uri = url_for('auth.google_callback', _external=True)
    
    if not client_id:
        flash("Google login is not configured", "error")
        return redirect(url_for('auth.login'))
    
    # Store the next URL in session if provided
    if request.args.get('next'):
        session['oauth_next'] = request.args.get('next')
    
    # Generate a state parameter to prevent CSRF
    state = str(uuid.uuid4())
    session['oauth_state'] = state
    
    # Build the authorization URL
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'email profile',
        'state': state
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    return redirect(auth_url)

@auth_bp.route('/google-callback')
def google_callback():
    """Handle Google OAuth callback."""
    # Verify state parameter
    state = request.args.get('state')
    stored_state = session.pop('oauth_state', None)
    
    if not state or state != stored_state:
        flash("Authorization failed. Please try again.", "error")
        return redirect(url_for('auth.login'))
    
    # Check for error
    if request.args.get('error'):
        flash(f"Authorization error: {request.args.get('error')}", "error")
        return redirect(url_for('auth.login'))
    
    # Exchange code for access token
    code = request.args.get('code')
    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
    redirect_uri = url_for('auth.google_callback', _external=True)
    
    token_url = "https://oauth2.googleapis.com/token"
    token_payload = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    try:
        token_response = requests.post(token_url, data=token_payload)
        token_data = token_response.json()
        
        if 'error' in token_data:
            flash(f"Token error: {token_data['error']}", "error")
            return redirect(url_for('auth.login'))
        
        # Get user info
        access_token = token_data['access_token']
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {'Authorization': f"Bearer {access_token}"}
        
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo = userinfo_response.json()
        
        # Check if user exists
        email = userinfo.get('email')
        if not email:
            flash("Could not retrieve email from Google", "error")
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(email=email).first()
        
        # Create user if not exists
        if not user:
            user = User(
                email=email,
                name=userinfo.get('name'),
                auth_provider='google',
                auth_provider_id=userinfo.get('sub')
            )
            db.session.add(user)
            db.session.commit()
        # Update existing user with Google auth info if they previously used email login
        elif not user.auth_provider:
            user.auth_provider = 'google'
            user.auth_provider_id = userinfo.get('sub')
            db.session.commit()
        
        # Log in user
        login_user(user, remember=True)
        
        # Redirect to next URL or default
        next_url = session.pop('oauth_next', None)
        if next_url:
            return redirect(next_url)
        
        # Check if there's a pending activity
        if session.get('activity_pending'):
            return redirect(url_for('main.create_activity'))
        
        return redirect(url_for('main.index'))
    
    except Exception as e:
        current_app.logger.error(f"Google OAuth error: {str(e)}")
        flash("An error occurred during Google login", "error")
        return redirect(url_for('auth.login'))

@auth_bp.route('/apple-login')
def apple_login():
    """Initiate Apple OAuth login flow."""
    # Apple OAuth configuration
    client_id = current_app.config.get('APPLE_CLIENT_ID')
    redirect_uri = url_for('auth.apple_callback', _external=True)
    
    if not client_id:
        flash("Apple login is not configured", "error")
        return redirect(url_for('auth.login'))
    
    # Store the next URL in session if provided
    if request.args.get('next'):
        session['oauth_next'] = request.args.get('next')
    
    # Generate a state parameter to prevent CSRF
    state = str(uuid.uuid4())
    session['oauth_state'] = state
    
    # Build the authorization URL
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'name email',
        'state': state,
        'response_mode': 'form_post'
    }
    
    auth_url = f"https://appleid.apple.com/auth/authorize?{urlencode(params)}"
    return redirect(auth_url)

@auth_bp.route('/apple-callback', methods=['GET', 'POST'])
def apple_callback():
    """Handle Apple OAuth callback."""
    # Apple sends data via POST
    if request.method == 'POST':
        # Verify state parameter
        state = request.form.get('state')
        stored_state = session.pop('oauth_state', None)
        
        if not state or state != stored_state:
            flash("Authorization failed. Please try again.", "error")
            return redirect(url_for('auth.login'))
        
        # Check for error
        if request.form.get('error'):
            flash(f"Authorization error: {request.form.get('error')}", "error")
            return redirect(url_for('auth.login'))
        
        # Get the code
        code = request.form.get('code')
        
        # Exchange code for tokens (implementation depends on Apple JWT requirements)
        try:
            # For simplicity, we'll log the user in based on the identity token
            id_token = request.form.get('id_token')
            
            # In a real implementation, you would:
            # 1. Verify the token's signature (requires a JWT library)
            # 2. Extract user info from the token
            
            # Parse user info from token (simplified)
            # In production, properly decode and verify the JWT
            user_info = json.loads(request.form.get('user', '{}'))
            
            email = user_info.get('email')
            if not email:
                flash("Could not retrieve email from Apple", "error")
                return redirect(url_for('auth.login'))
            
            # Check if user exists
            user = User.query.filter_by(email=email).first()
            
            # Create user if not exists
            if not user:
                user = User(
                    email=email,
                    name=user_info.get('name', {}).get('firstName', '') + ' ' + user_info.get('name', {}).get('lastName', ''),
                    auth_provider='apple',
                    auth_provider_id=user_info.get('sub')
                )
                db.session.add(user)
                db.session.commit()
            # Update existing user with Apple auth info if they previously used email login
            elif not user.auth_provider:
                user.auth_provider = 'apple'
                user.auth_provider_id = user_info.get('sub')
                db.session.commit()
            
            # Log in user
            login_user(user, remember=True)
            
            # Redirect to next URL or default
            next_url = session.pop('oauth_next', None)
            if next_url:
                return redirect(next_url)
            
            # Check if there's a pending activity
            if session.get('activity_pending'):
                return redirect(url_for('main.create_activity'))
            
            return redirect(url_for('main.index'))
        
        except Exception as e:
            current_app.logger.error(f"Apple OAuth error: {str(e)}")
            flash("An error occurred during Apple login", "error")
            return redirect(url_for('auth.login'))
    
    # If it's a GET request, redirect to login
    return redirect(url_for('auth.login'))
