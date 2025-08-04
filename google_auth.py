# google_auth.py - Updated with Gmail API support for 2FA and Universal Email Service integration
"""
Enhanced Google OAuth integration with Gmail API support for 2FA
Now supports universal email service for ALL users
"""

import os
import secrets
import requests
import json
import time
import base64
from urllib.parse import urlencode
from flask import Blueprint, request, redirect, url_for, session, flash, current_app, render_template
from flask_login import login_user, current_user, login_required
from models import db, User, TwoFactorAuth
from security import log_security_event
from datetime import datetime, timedelta
from email_service import EmailService

# FIXED: Correct email imports for Python 3.13
try:
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
except ImportError:
    # Fallback for any other Python version issues
    from email.mime import text as mime_text_module
    from email.mime import multipart as mime_multipart_module
    MIMEText = mime_text_module.MIMEText
    MIMEMultipart = mime_multipart_module.MIMEMultipart

# Create the Google auth blueprint
simple_google_auth = Blueprint('simple_google_auth', __name__)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

# UPDATED: OAuth scopes to include Gmail
OAUTH_SCOPES = [
    'openid',
    'email', 
    'profile',
    'https://www.googleapis.com/auth/gmail.send'  # Added Gmail send permission
]

# Manual endpoint configuration as fallback
MANUAL_GOOGLE_ENDPOINTS = {
    'authorization_endpoint': 'https://accounts.google.com/o/oauth2/v2/auth',
    'token_endpoint': 'https://oauth2.googleapis.com/token',
    'userinfo_endpoint': 'https://www.googleapis.com/oauth2/v2/userinfo',
    'issuer': 'https://accounts.google.com'
}

def get_google_provider_cfg(max_retries=3, timeout=15):
    """Get Google's OAuth configuration with fallback to manual endpoints"""
    
    # Discovery URLs to try
    discovery_urls = [
        "https://accounts.google.com/.well-known/openid_configuration",
        "https://accounts.google.com/.well-known/openid-configuration"
    ]
    
    # Try discovery endpoints first
    for discovery_url in discovery_urls:
        for attempt in range(max_retries):
            try:
                current_app.logger.info(f"Trying discovery URL: {discovery_url} (attempt {attempt + 1}/{max_retries})")
                
                headers = {
                    'User-Agent': 'SilverSage/1.0.0 Flask OAuth Client',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive'
                }
                
                response = requests.get(
                    discovery_url, 
                    timeout=timeout,
                    headers=headers,
                    verify=True
                )
                
                if response.status_code == 200:
                    try:
                        config = response.json()
                        current_app.logger.info(f"Successfully fetched config from {discovery_url}")
                        
                        # Validate required endpoints
                        required_endpoints = ['authorization_endpoint', 'token_endpoint']
                        if all(config.get(ep) for ep in required_endpoints):
                            return config
                        else:
                            current_app.logger.warning(f"Missing endpoints in response from {discovery_url}")
                    except json.JSONDecodeError:
                        current_app.logger.warning(f"Invalid JSON from {discovery_url}")
                        
            except requests.exceptions.Timeout:
                current_app.logger.warning(f"Timeout for {discovery_url} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(1)
            except requests.exceptions.RequestException as e:
                current_app.logger.warning(f"Request error for {discovery_url}: {e}")
                break
            except Exception as e:
                current_app.logger.warning(f"Unexpected error for {discovery_url}: {e}")
                break
    
    # Use manual endpoints as fallback
    current_app.logger.info("All discovery endpoints failed, using manual configuration")
    return MANUAL_GOOGLE_ENDPOINTS

@simple_google_auth.route('/auth/google')
def google_login():
    """Initiate Google OAuth login with Gmail permissions"""
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash('Google OAuth is not configured. Please contact an administrator.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        google_provider_cfg = get_google_provider_cfg()
        
        if not google_provider_cfg:
            flash('Google authentication service is currently unavailable. Please try again later.', 'error')
            return redirect(url_for('auth.login'))
        
        authorization_endpoint = google_provider_cfg.get("authorization_endpoint")
        if not authorization_endpoint:
            flash('Google authentication configuration is invalid.', 'error')
            return redirect(url_for('auth.login'))
        
        # Generate state for security
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        # Build authorization URL with Gmail scope
        redirect_uri = url_for('simple_google_auth.google_callback', _external=True)
        
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(OAUTH_SCOPES),  # Updated with Gmail scope
            'response_type': 'code',
            'state': state,
            'access_type': 'offline',  # Important for refresh tokens
            'prompt': 'consent'  # Force consent to get refresh token
        }
        
        authorization_url = authorization_endpoint + '?' + urlencode(params)
        
        log_security_event('Google OAuth login initiated with Gmail permissions')
        return redirect(authorization_url)
        
    except Exception as e:
        current_app.logger.error(f"Error in google_login: {str(e)}")
        flash('An error occurred while setting up Google login. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@simple_google_auth.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Verify state parameter
        received_state = request.args.get('state')
        stored_state = session.get('oauth_state')
        
        if received_state != stored_state:
            flash('Security validation failed. Please try logging in again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Handle OAuth errors
        if 'error' in request.args:
            error = request.args.get('error')
            if error == 'access_denied':
                flash('You cancelled the Google login.', 'info')
            else:
                flash(f'Google authentication failed: {error}', 'error')
            return redirect(url_for('auth.login'))
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            flash('No authorization code received from Google.', 'error')
            return redirect(url_for('auth.login'))
        
        # Get Google's configuration
        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            flash('Google authentication service unavailable during token exchange.', 'error')
            return redirect(url_for('auth.login'))
        
        token_endpoint = google_provider_cfg.get("token_endpoint")
        
        # Exchange code for tokens
        token_data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': url_for('simple_google_auth.google_callback', _external=True)
        }
        
        token_response = requests.post(token_endpoint, data=token_data, timeout=15)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        if 'error' in tokens:
            flash(f'Token exchange failed: {tokens.get("error_description", "Unknown error")}', 'error')
            return redirect(url_for('auth.login'))
        
        # Get user info
        userinfo_endpoint = google_provider_cfg.get("userinfo_endpoint", MANUAL_GOOGLE_ENDPOINTS['userinfo_endpoint'])
        
        headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
        userinfo_response = requests.get(userinfo_endpoint, headers=headers, timeout=10)
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
        
        # Extract user information
        google_id = userinfo.get('sub') or userinfo.get('id')
        email = userinfo.get('email')
        first_name = userinfo.get('given_name', '')
        last_name = userinfo.get('family_name', '')
        
        if not email:
            flash('Could not get email from your Google account.', 'error')
            return redirect(url_for('auth.login'))
        
        # Create or update user
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Update existing user with new tokens
            user.google_id = google_id
            user.google_access_token = tokens.get('access_token')
            user.google_refresh_token = tokens.get('refresh_token')  # This is crucial for Gmail API
            user.email_verified = True
            
            db.session.commit()
            
            login_user(user, remember=True)
            log_security_event(f'User logged in via Google: {user.username}')
            flash(f'Welcome back, {user.first_name or user.username}!', 'success')
        else:
            # Create new user
            username = email.split('@')[0]
            
            # Ensure unique username
            counter = 1
            original_username = username
            while User.query.filter_by(username=username).first():
                username = f"{original_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                google_id=google_id,
                google_access_token=tokens.get('access_token'),
                google_refresh_token=tokens.get('refresh_token'),
                email_verified=True
            )
            
            user.set_password(secrets.token_urlsafe(32))
            
            db.session.add(user)
            db.session.commit()
            
            login_user(user, remember=True)
            log_security_event(f'New user registered via Google: {user.username}')
            flash(f'Welcome to SilverSage, {user.first_name or user.username}!', 'success')
        
        # Clean up session
        session.pop('oauth_state', None)
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        current_app.logger.error(f"Error in OAuth callback: {str(e)}")
        flash('An error occurred during Google authentication.', 'error')
        return redirect(url_for('auth.login'))

def refresh_google_token(user):
    """Refresh Google access token using refresh token"""
    if not user.google_refresh_token:
        return False
    
    try:
        token_data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'refresh_token': user.google_refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data=token_data,
            timeout=10
        )
        
        if response.status_code == 200:
            tokens = response.json()
            user.google_access_token = tokens.get('access_token')
            
            # Sometimes a new refresh token is provided
            if 'refresh_token' in tokens:
                user.google_refresh_token = tokens['refresh_token']
            
            db.session.commit()
            return True
        else:
            current_app.logger.error(f"Token refresh failed: {response.text}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error refreshing token: {str(e)}")
        return False

def send_2fa_email(user, code):
    """Send 2FA code via Gmail API (legacy function - kept for compatibility)"""
    if not user.google_access_token:
        current_app.logger.error("No Google access token for user")
        return False
    
    try:
        # Create email message
        message = MIMEMultipart()
        message['To'] = user.email
        message['From'] = user.email  # Send from user's own email
        message['Subject'] = 'SilverSage - Your Security Code'
        
        # Email body
        body = f"""
        Hello {user.first_name or user.username},
        
        Your SilverSage security code is: {code}
        
        This code will expire in 10 minutes.
        
        If you didn't request this code, please contact support immediately.
        
        Best regards,
        The SilverSage Team
        """
        
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send via Gmail API
        gmail_url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
        headers = {
            'Authorization': f'Bearer {user.google_access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'raw': raw_message
        }
        
        response = requests.post(gmail_url, headers=headers, json=data, timeout=15)
        
        # If token expired, try to refresh
        if response.status_code == 401:
            current_app.logger.info("Access token expired, attempting refresh")
            if refresh_google_token(user):
                # Retry with new token
                headers['Authorization'] = f'Bearer {user.google_access_token}'
                response = requests.post(gmail_url, headers=headers, json=data, timeout=15)
            else:
                current_app.logger.error("Failed to refresh token")
                return False
        
        if response.status_code == 200:
            current_app.logger.info(f"2FA email sent successfully to {user.email}")
            return True
        else:
            current_app.logger.error(f"Gmail API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error sending 2FA email: {str(e)}")
        return False

# =============================================================================
# 2FA Management Routes - Updated to use Universal Email Service
# =============================================================================

@simple_google_auth.route('/security/enable-2fa', methods=['GET', 'POST'])
@login_required
def enable_2fa():
    """Enable 2FA for user account using universal email service"""
    if current_user.has_2fa_enabled():
        flash('Two-factor authentication is already enabled.', 'info')
        return redirect(url_for('auth.security_settings'))
    
    if request.method == 'POST':
        # Generate test code
        test_code = f"{secrets.randbelow(1000000):06d}"
        
        # Create or get 2FA record
        two_fa = current_user.two_factor_auth
        if not two_fa:
            two_fa = TwoFactorAuth(user_id=current_user.id)
            db.session.add(two_fa)
        
        two_fa.temp_code = test_code
        two_fa.temp_code_expires = datetime.utcnow() + timedelta(minutes=10)
        
        # Generate backup codes
        backup_codes = [f"{secrets.randbelow(100000000):08d}" for _ in range(10)]
        two_fa.backup_codes = ','.join(backup_codes)
        
        db.session.commit()
        
        # Use universal EmailService instead of Google-specific sending
        if EmailService.send_2fa_code_email(current_user, test_code):
            session['2fa_setup_user_id'] = current_user.id
            flash('A test verification code has been sent to your email.', 'info')
            return redirect(url_for('simple_google_auth.verify_2fa_setup'))
        else:
            flash('Failed to send verification email. Please try again or contact support.', 'error')
            log_security_event(f'2FA setup email failed: {current_user.username}', success=False)
    
    return render_template('auth/enable_2fa.html')

@simple_google_auth.route('/security/verify-2fa-setup', methods=['GET', 'POST'])
@login_required
def verify_2fa_setup():
    """Verify 2FA setup with test code"""
    if '2fa_setup_user_id' not in session:
        flash('No 2FA setup session found.', 'error')
        return redirect(url_for('auth.security_settings'))
    
    if current_user.has_2fa_enabled():
        flash('Two-factor authentication is already enabled.', 'info')
        return redirect(url_for('auth.security_settings'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        two_fa = current_user.two_factor_auth
        
        if two_fa and two_fa.verify_temp_code(code):
            # Enable 2FA
            two_fa.is_enabled = True
            two_fa.temp_code = None
            two_fa.temp_code_expires = None
            db.session.commit()
            
            # Clear session
            session.pop('2fa_setup_user_id', None)
            
            log_security_event(f'2FA enabled for user: {current_user.username}')
            flash('Two-factor authentication has been successfully enabled!', 'success')
            
            # Show backup codes
            backup_codes = two_fa.backup_codes.split(',')
            return render_template('auth/2fa_enabled.html', backup_codes=backup_codes)
        else:
            flash('Invalid or expired verification code.', 'error')
            log_security_event(f'Invalid 2FA setup code: {current_user.username}', success=False)
    
    return render_template('auth/verify_2fa_setup.html')

@simple_google_auth.route('/security/disable-2fa', methods=['GET', 'POST'])
@login_required
def disable_2fa():
    """Disable 2FA for user account"""
    if not current_user.has_2fa_enabled():
        flash('Two-factor authentication is not enabled.', 'info')
        return redirect(url_for('auth.security_settings'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm')
        
        if not confirm:
            flash('You must confirm that you understand the security implications.', 'error')
            return render_template('auth/disable_2fa.html')
        
        if current_user.check_password(password):
            # Disable 2FA
            two_fa = current_user.two_factor_auth
            if two_fa:
                db.session.delete(two_fa)
                db.session.commit()
            
            log_security_event(f'2FA disabled for user: {current_user.username}')
            flash('Two-factor authentication has been disabled. Your account is now less secure.', 'warning')
            return redirect(url_for('auth.security_settings'))
        else:
            flash('Incorrect password.', 'error')
            log_security_event(f'Failed 2FA disable attempt: {current_user.username}', success=False)
    
    return render_template('auth/disable_2fa.html')

@simple_google_auth.route('/security/regenerate-backup-codes', methods=['POST'])
@login_required
def regenerate_backup_codes():
    """Regenerate backup codes for 2FA"""
    if not current_user.has_2fa_enabled():
        flash('Two-factor authentication is not enabled.', 'error')
        return redirect(url_for('auth.security_settings'))
    
    two_fa = current_user.two_factor_auth
    if two_fa:
        # Generate new backup codes
        backup_codes = [f"{secrets.randbelow(100000000):08d}" for _ in range(10)]
        two_fa.backup_codes = ','.join(backup_codes)
        db.session.commit()
        
        log_security_event(f'2FA backup codes regenerated: {current_user.username}')
        flash('New backup codes have been generated. Please save them securely.', 'success')
        
        return render_template('auth/2fa_enabled.html', backup_codes=backup_codes)
    
    flash('Error regenerating backup codes.', 'error')
    return redirect(url_for('auth.security_settings'))

# =============================================================================
# Legacy and Debug Routes
# =============================================================================

@simple_google_auth.route('/auth/google/debug')
def google_debug():
    """Debug route for Google OAuth configuration"""
    if not current_app.debug:
        return "Debug route only available in debug mode", 403
    
    # Test Gmail API access for current user
    gmail_status = "Not available"
    if current_user.is_authenticated and current_user.google_access_token:
        try:
            headers = {'Authorization': f'Bearer {current_user.google_access_token}'}
            response = requests.get(
                'https://gmail.googleapis.com/gmail/v1/users/me/profile',
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                gmail_status = "✅ Gmail API accessible"
            elif response.status_code == 401:
                gmail_status = "🔄 Token needs refresh"
            else:
                gmail_status = f"❌ Error: {response.status_code}"
        except Exception as e:
            gmail_status = f"❌ Exception: {str(e)}"
    
    # Test Universal Email Service
    email_service_status = "Not tested"
    if current_user.is_authenticated:
        success, message = EmailService.test_email_configuration()
        email_service_status = f"{'✅' if success else '❌'} {message}"
    
    config_status = {
        'GOOGLE_CLIENT_ID': 'Set' if GOOGLE_CLIENT_ID else 'Not set',
        'GOOGLE_CLIENT_SECRET': 'Set' if GOOGLE_CLIENT_SECRET else 'Not set',
        'OAUTH_SCOPES': OAUTH_SCOPES,
        'GMAIL_API_STATUS': gmail_status,
        'UNIVERSAL_EMAIL_SERVICE': email_service_status,
        'USER_2FA_STATUS': current_user.has_2fa_enabled() if current_user.is_authenticated else 'Not logged in'
    }
    
    return f"""
    <h1>Google OAuth & Email Debug</h1>
    <pre>{json.dumps(config_status, indent=2)}</pre>
    <h2>Available Routes:</h2>
    <ul>
        <li><a href="{url_for('simple_google_auth.google_login')}">Test Google Login</a></li>
        <li><a href="{url_for('auth.security_settings')}">Security Settings</a></li>
        <li><a href="{url_for('auth.test_2fa')}">Test 2FA Email</a></li>
        <li><a href="{url_for('auth.login')}">Back to Login</a></li>
    </ul>
    """