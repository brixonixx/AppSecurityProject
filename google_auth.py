# google_auth.py - FIXED with correct Google OAuth discovery endpoint
"""
Fixed Google OAuth integration with correct discovery endpoint and manual fallback
"""

import os
import secrets
import requests
import json
import time
from urllib.parse import urlencode
from flask import Blueprint, request, redirect, url_for, session, flash, current_app
from flask_login import login_user, current_user
from models import db, User
from security import log_security_event

# Create the Google auth blueprint
simple_google_auth = Blueprint('simple_google_auth', __name__)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

# FIXED: Updated discovery URLs and manual endpoints as fallback
GOOGLE_DISCOVERY_URLS = [
    "https://accounts.google.com/.well-known/openid_configuration",
    "https://accounts.google.com/.well-known/openid-configuration",  # Alternative
    "https://www.googleapis.com/oauth2/v3/certs"  # Another endpoint to try
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
    
    # First try the discovery endpoints
    for discovery_url in GOOGLE_DISCOVERY_URLS:
        for attempt in range(max_retries):
            try:
                current_app.logger.info(f"Trying discovery URL: {discovery_url} (attempt {attempt + 1}/{max_retries})")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
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
                
                current_app.logger.info(f"Response status: {response.status_code}")
                
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
                break  # Try next URL
            except Exception as e:
                current_app.logger.warning(f"Unexpected error for {discovery_url}: {e}")
                break
    
    # If all discovery attempts failed, use manual endpoints
    current_app.logger.info("All discovery endpoints failed, using manual configuration")
    
    # Test that our manual endpoints are reachable
    try:
        test_response = requests.head(MANUAL_GOOGLE_ENDPOINTS['authorization_endpoint'], timeout=5)
        if test_response.status_code < 500:  # Any response except server error is good
            current_app.logger.info("Manual endpoints appear reachable, using fallback configuration")
            return MANUAL_GOOGLE_ENDPOINTS
    except Exception as e:
        current_app.logger.error(f"Even manual endpoints are unreachable: {e}")
    
    return None

@simple_google_auth.route('/auth/google')
def google_login():
    """Initiate Google OAuth login with enhanced error handling"""
    
    # Configuration checks
    if not GOOGLE_CLIENT_ID:
        current_app.logger.error("GOOGLE_CLIENT_ID not configured")
        flash('Google OAuth is not configured - missing Client ID. Please contact an administrator.', 'error')
        return redirect(url_for('auth.login'))
    
    if not GOOGLE_CLIENT_SECRET:
        current_app.logger.error("GOOGLE_CLIENT_SECRET not configured")
        flash('Google OAuth is not configured - missing Client Secret. Please contact an administrator.', 'error')
        return redirect(url_for('auth.login'))
    
    current_app.logger.info(f"Initiating Google OAuth with Client ID: {GOOGLE_CLIENT_ID[:10]}...")
    
    try:
        # Get Google's configuration
        google_provider_cfg = get_google_provider_cfg()
        
        if not google_provider_cfg:
            current_app.logger.error("Could not fetch Google OAuth configuration")
            flash('Google authentication service is currently unavailable. This may be due to network issues or temporary Google service problems. Please try again later.', 'error')
            return redirect(url_for('auth.login'))
        
        authorization_endpoint = google_provider_cfg.get("authorization_endpoint")
        if not authorization_endpoint:
            current_app.logger.error("No authorization endpoint in Google config")
            flash('Google authentication configuration is invalid - missing authorization endpoint.', 'error')
            return redirect(url_for('auth.login'))
        
        # Generate state for security
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        current_app.logger.info(f"Generated OAuth state: {state[:10]}...")
        
        # Build authorization URL
        redirect_uri = url_for('simple_google_auth.google_callback', _external=True)
        current_app.logger.info(f"Using redirect URI: {redirect_uri}")
        
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'scope': 'openid email profile',
            'response_type': 'code',
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        authorization_url = authorization_endpoint + '?' + urlencode(params)
        current_app.logger.info(f"Redirecting to: {authorization_url[:100]}...")
        
        log_security_event('Google OAuth login initiated')
        return redirect(authorization_url)
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error in google_login: {str(e)}")
        flash('An unexpected error occurred while setting up Google login. Please try again or use regular login.', 'error')
        return redirect(url_for('auth.login'))

@simple_google_auth.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback with comprehensive error handling"""
    try:
        current_app.logger.info("Google OAuth callback received")
        current_app.logger.info(f"Request args: {dict(request.args)}")
        
        # Verify state parameter
        received_state = request.args.get('state')
        stored_state = session.get('oauth_state')
        
        if received_state != stored_state:
            current_app.logger.error(f"OAuth state mismatch")
            flash('Security validation failed. Please try logging in again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Handle OAuth error responses
        if 'error' in request.args:
            error = request.args.get('error')
            error_description = request.args.get('error_description', '')
            current_app.logger.error(f"OAuth error from Google: {error} - {error_description}")
            
            if error == 'access_denied':
                flash('You cancelled the Google login. You can try again or use regular login.', 'info')
            else:
                flash(f'Google authentication failed: {error_description or error}', 'error')
            return redirect(url_for('auth.login'))
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            current_app.logger.error("No authorization code received from Google")
            flash('No authorization code received from Google. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        current_app.logger.info(f"Received authorization code: {code[:10]}...")
        
        # Get Google's configuration
        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            flash('Google authentication service unavailable during token exchange. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        token_endpoint = google_provider_cfg.get("token_endpoint")
        if not token_endpoint:
            current_app.logger.error("No token endpoint in Google config")
            flash('Google authentication configuration error. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Exchange code for tokens
        token_data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': url_for('simple_google_auth.google_callback', _external=True)
        }
        
        current_app.logger.info("Exchanging authorization code for tokens...")
        
        # Try token exchange with retry
        for attempt in range(3):
            try:
                token_response = requests.post(
                    token_endpoint, 
                    data=token_data, 
                    timeout=15,
                    headers={'User-Agent': 'SilverSage/1.0.0 Flask OAuth Client'}
                )
                token_response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                if attempt < 2:
                    current_app.logger.warning(f"Token exchange timeout, attempt {attempt + 1}/3")
                    time.sleep(2)
                else:
                    raise
            except requests.exceptions.ConnectionError:
                if attempt < 2:
                    current_app.logger.warning(f"Token exchange connection error, attempt {attempt + 1}/3")
                    time.sleep(2)
                else:
                    raise
        
        tokens = token_response.json()
        current_app.logger.info(f"Token response received with keys: {list(tokens.keys())}")
        
        if 'error' in tokens:
            error_msg = tokens.get("error_description", tokens.get("error", "Unknown error"))
            current_app.logger.error(f"Token exchange error: {error_msg}")
            flash(f'Google authentication failed during token exchange: {error_msg}', 'error')
            return redirect(url_for('auth.login'))
        
        if 'access_token' not in tokens:
            current_app.logger.error("No access token in response")
            flash('Failed to get access token from Google. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Get user info from Google
        userinfo_endpoint = google_provider_cfg.get("userinfo_endpoint", MANUAL_GOOGLE_ENDPOINTS['userinfo_endpoint'])
        
        headers = {
            'Authorization': f'Bearer {tokens["access_token"]}',
            'User-Agent': 'SilverSage/1.0.0 Flask OAuth Client'
        }
        
        current_app.logger.info("Fetching user info from Google...")
        
        for attempt in range(3):
            try:
                userinfo_response = requests.get(userinfo_endpoint, headers=headers, timeout=10)
                userinfo_response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                if attempt < 2:
                    current_app.logger.warning(f"User info fetch timeout, attempt {attempt + 1}/3")
                    time.sleep(1)
                else:
                    raise
        
        userinfo = userinfo_response.json()
        current_app.logger.info(f"User info received with keys: {list(userinfo.keys())}")
        
        # Extract and validate user information
        google_id = userinfo.get('sub') or userinfo.get('id')
        email = userinfo.get('email')
        first_name = userinfo.get('given_name', '')
        last_name = userinfo.get('family_name', '')
        
        current_app.logger.info(f"User email from Google: {email}")
        
        if not email:
            current_app.logger.error("No email in Google user info")
            flash('Could not get email from your Google account. Please ensure your Google account has an email address.', 'error')
            return redirect(url_for('auth.login'))
        
        # Create or update user
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Existing user - update Google info
            user.google_id = google_id
            user.google_access_token = tokens.get('access_token')
            user.google_refresh_token = tokens.get('refresh_token')
            user.email_verified = True
            
            db.session.commit()
            
            login_user(user, remember=True)
            log_security_event(f'User logged in via Google: {user.username}')
            flash(f'Welcome back, {user.first_name or user.username}!', 'success')
        else:
            # Create new user
            username = email.split('@')[0]
            
            # Ensure username is unique
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
            
            # Set a random password
            user.set_password(secrets.token_urlsafe(32))
            
            db.session.add(user)
            db.session.commit()
            
            login_user(user, remember=True)
            log_security_event(f'New user registered via Google: {user.username}')
            flash(f'Welcome to SilverSage, {user.first_name or user.username}!', 'success')
        
        # Clean up session
        session.pop('oauth_state', None)
        
        return redirect(url_for('dashboard'))
        
    except requests.exceptions.Timeout as e:
        current_app.logger.error(f"Timeout during OAuth callback: {str(e)}")
        flash('Google authentication timed out. Please check your internet connection and try again.', 'error')
        return redirect(url_for('auth.login'))
    except requests.exceptions.ConnectionError as e:
        current_app.logger.error(f"Connection error during OAuth callback: {str(e)}")
        flash('Network error during Google authentication. Please check your internet connection and try again.', 'error')
        return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in OAuth callback: {str(e)}")
        flash('An unexpected error occurred during Google authentication. Please try again or use regular login.', 'error')
        return redirect(url_for('auth.login'))

# Simple password reset functionality
@simple_google_auth.route('/auth/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Simple password reset request"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            reset_token = secrets.token_urlsafe(32)
            session[f'reset_token_{email}'] = {
                'token': reset_token,
                'expires': 'implement_expiry_logic'
            }
            flash(f'Password reset initiated. Token: {reset_token} (This is for development only)', 'info')
            
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))
    
    return '''
    <div style="max-width: 400px; margin: 50px auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
        <h2>Reset Password</h2>
        <form method="POST">
            <div style="margin-bottom: 15px;">
                <label for="email">Email Address:</label><br>
                <input type="email" name="email" id="email" required style="width: 100%; padding: 8px; margin-top: 5px;">
            </div>
            <button type="submit" style="background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">Send Reset Link</button>
            <a href="''' + url_for('auth.login') + '''" style="margin-left: 10px;">Back to Login</a>
        </form>
    </div>
    '''

# Enhanced debug route with network testing
@simple_google_auth.route('/auth/google/debug')
def google_debug():
    """Enhanced debug route with network diagnostics"""
    if not current_app.debug:
        return "Debug route only available in debug mode", 403
    
    config_status = {
        'GOOGLE_CLIENT_ID': 'Set' if GOOGLE_CLIENT_ID else 'Not set',
        'GOOGLE_CLIENT_SECRET': 'Set' if GOOGLE_CLIENT_SECRET else 'Not set',
        'GOOGLE_CLIENT_ID_LENGTH': len(GOOGLE_CLIENT_ID) if GOOGLE_CLIENT_ID else 0,
        'GOOGLE_CLIENT_SECRET_LENGTH': len(GOOGLE_CLIENT_SECRET) if GOOGLE_CLIENT_SECRET else 0,
    }
    
    # Test Google discovery endpoint and manual fallback
    try:
        start_time = time.time()
        
        # Test basic connectivity first
        basic_test_url = 'https://google.com'
        try:
            basic_response = requests.get(basic_test_url, timeout=5)
            basic_connectivity = f'✅ Success ({basic_response.status_code})'
        except Exception as e:
            basic_connectivity = f'❌ Error: {str(e)}'
        
        config_status['BASIC_CONNECTIVITY'] = basic_connectivity
        
        # Test our configuration function
        google_config = get_google_provider_cfg()
        end_time = time.time()
        
        if google_config:
            config_status['GOOGLE_DISCOVERY'] = f'✅ Available ({end_time - start_time:.2f}s)'
            config_status['ENDPOINTS'] = {
                'authorization_endpoint': google_config.get('authorization_endpoint', 'Missing'),
                'token_endpoint': google_config.get('token_endpoint', 'Missing'),
                'userinfo_endpoint': google_config.get('userinfo_endpoint', 'Missing'),
                'source': 'Manual Fallback' if google_config == MANUAL_GOOGLE_ENDPOINTS else 'Discovery'
            }
        else:
            config_status['GOOGLE_DISCOVERY'] = f'❌ Failed ({end_time - start_time:.2f}s)'
            config_status['DISCOVERY_DETAILS'] = {
                'error': 'All discovery URLs and manual endpoints failed',
                'tested_urls': GOOGLE_DISCOVERY_URLS,
                'manual_endpoints': MANUAL_GOOGLE_ENDPOINTS
            }
                
    except Exception as e:
        config_status['GOOGLE_DISCOVERY'] = f'❌ Error: {str(e)}'
    
    # Generate HTML response with better formatting
    html_response = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google OAuth Debug Information</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            .success {{ color: #28a745; }}
            .error {{ color: #dc3545; }}
            .warning {{ color: #ffc107; }}
            .info {{ background: #e9ecef; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            pre {{ background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            .diagnostic {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <h1>🔧 Google OAuth Debug Information</h1>
        
        <div class="info">
            <h3>Configuration Status</h3>
            <ul>
                <li>Client ID: <span class="{'success' if config_status['GOOGLE_CLIENT_ID'] == 'Set' else 'error'}">{config_status['GOOGLE_CLIENT_ID']}</span></li>
                <li>Client Secret: <span class="{'success' if config_status['GOOGLE_CLIENT_SECRET'] == 'Set' else 'error'}">{config_status['GOOGLE_CLIENT_SECRET']}</span></li>
                <li>Basic Connectivity: <span class="{'success' if '✅' in config_status.get('BASIC_CONNECTIVITY', '') else 'error'}">{config_status.get('BASIC_CONNECTIVITY', 'Not tested')}</span></li>
                <li>Google Configuration: <span class="{'success' if '✅' in config_status.get('GOOGLE_DISCOVERY', '') else 'error'}">{config_status.get('GOOGLE_DISCOVERY', 'Not tested')}</span></li>
            </ul>
        </div>
        
        <div class="diagnostic">
            <h3>🎉 GOOD NEWS!</h3>
            <p>This version uses <strong>manual fallback endpoints</strong> that should work even if Google's discovery endpoint is having issues.</p>
            <ol>
                <li><strong>If Configuration shows ✅:</strong> Google OAuth should now work! Try the login flow.</li>
                <li><strong>If still having issues:</strong> Check the Flask application logs for detailed error messages.</li>
                <li><strong>Test the flow:</strong> Click "Start Google OAuth Flow" below to test.</li>
            </ol>
        </div>
        
        <h3>Full Debug Information</h3>
        <pre>{json.dumps(config_status, indent=2)}</pre>
        
        <div class="info">
            <h3>Test URLs</h3>
            <ul>
                <li><a href="{url_for('simple_google_auth.google_login')}" target="_blank">🚀 Start Google OAuth Flow</a></li>
                <li><a href="{url_for('auth.login')}">Back to Login Page</a></li>
                <li><a href="/test-db">System Status Page</a></li>
            </ul>
        </div>
        
        <p><strong>⚠️ Important:</strong> Remove this debug route in production!</p>
    </body>
    </html>
    """
    
    return html_response

# Helper function for 2FA (placeholder)
def send_2fa_code(user, code):
    """Send 2FA code via email - placeholder for future implementation"""
    current_app.logger.info(f"2FA code for {user.email}: {code}")
    return True