# Complete auth.py - Enhanced with Google OAuth and 2FA support
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
import os
import secrets
from models import db, User, TwoFactorAuth
from forms import (LoginForm, RegistrationForm, ProfileForm, ChangePasswordForm, 
                  TwoFactorForm, ForgotPasswordForm, ResetPasswordForm,
                  Enable2FAForm, Verify2FASetupForm, Disable2FAForm)
from security import log_security_event
from datetime import datetime, timedelta
from email_service import EmailService

auth = Blueprint('auth', __name__)

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_profile_picture(form_picture):
    """Save and resize profile picture"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'], picture_fn)
    
    # Resize image to save space and standardize
    output_size = (200, 200)
    img = Image.open(form_picture)
    img.thumbnail(output_size)
    img.save(picture_path)
    
    return picture_fn

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Enhanced login with universal 2FA support"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'error')
                log_security_event(f'Login attempt on deactivated account: {user.email}', success=False)
                return redirect(url_for('auth.login'))
            
            # Check if user has 2FA enabled
            if user.has_2fa_enabled():
                # Store user ID in session for 2FA verification
                session['pending_user_id'] = user.id
                session['remember_me'] = form.remember_me.data
                
                # Generate and send 2FA code
                two_fa_code = f"{secrets.randbelow(1000000):06d}"
                
                # Update 2FA record
                two_fa = user.two_factor_auth
                two_fa.temp_code = two_fa_code
                two_fa.temp_code_expires = datetime.utcnow() + timedelta(minutes=10)
                db.session.commit()
                
                # Send code via email to ANY user (not just Google users)
                if EmailService.send_2fa_code_email(user, two_fa_code):
                    flash('A verification code has been sent to your email.', 'info')
                    return redirect(url_for('auth.two_factor'))
                else:
                    flash('Failed to send 2FA code. Please try again later or contact support.', 'error')
                    log_security_event(f'2FA email send failed: {user.username}', success=False)
                    return redirect(url_for('auth.login'))
            else:
                # Normal login without 2FA
                login_user(user, remember=form.remember_me.data)
                user.last_login = datetime.utcnow()
                db.session.commit()
                log_security_event(f'User login: {user.username}')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            log_security_event(f'Failed login attempt for email: {form.email.data}', success=False)
    
    return render_template('login.html', form=form)

@auth.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    """Handle 2FA verification during login - works for ALL users"""
    if 'pending_user_id' not in session:
        flash('No pending authentication found.', 'error')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['pending_user_id'])
    if not user:
        session.pop('pending_user_id', None)
        flash('Authentication session expired.', 'error')
        return redirect(url_for('auth.login'))
    
    form = TwoFactorForm()
    if form.validate_on_submit():
        two_fa = user.two_factor_auth
        
        # Check main verification code
        if form.code.data and two_fa.verify_temp_code(form.code.data):
            # Clear temp code
            two_fa.temp_code = None
            two_fa.temp_code_expires = None
            db.session.commit()
            
            # Complete login
            remember_me = session.pop('remember_me', False)
            session.pop('pending_user_id', None)
            
            login_user(user, remember=remember_me)
            user.last_login = datetime.utcnow()
            db.session.commit()
            log_security_event(f'User login with 2FA: {user.username}')
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        
        # Check backup code
        elif form.backup_code.data and two_fa.is_backup_code_valid(form.backup_code.data):
            db.session.commit()
            
            # Complete login
            remember_me = session.pop('remember_me', False)
            session.pop('pending_user_id', None)
            
            login_user(user, remember=remember_me)
            user.last_login = datetime.utcnow()
            db.session.commit()
            log_security_event(f'User login with backup code: {user.username}')
            
            flash('You used a backup code. Consider generating new ones in Security Settings.', 'warning')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        
        else:
            flash('Invalid verification code. Please try again.', 'error')
            log_security_event(f'Failed 2FA attempt: {user.username}', success=False)
    
    return render_template('auth/two_factor.html', form=form, user=user)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.email.data)
        ).first()
        
        if existing_user:
            if existing_user.username == form.username.data:
                flash('Username already taken. Please choose another.', 'error')
            else:
                flash('Email already registered. Please login or use another email.', 'error')
            return redirect(url_for('auth.register'))
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        log_security_event(f'New user registered: {user.username}')
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    """User logout with session cleanup"""
    username = current_user.username
    logout_user()
    
    # Clear any pending sessions
    session.pop('pending_user_id', None)
    session.pop('remember_me', None)
    session.pop('2fa_setup_user_id', None)
    
    log_security_event(f'User logout: {username}')
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    form = ProfileForm()
    
    if form.validate_on_submit():
        if form.profile_picture.data:
            picture_file = save_profile_picture(form.profile_picture.data)
            current_user.profile_picture = picture_file
        
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.age = form.age.data
        current_user.contact_number = form.contact_number.data
        
        db.session.commit()
        log_security_event(f'Profile updated: {current_user.username}')
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('auth.profile'))
    
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.age.data = current_user.age
        form.contact_number.data = current_user.contact_number
    
    return render_template('profile.html', form=form)

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Password change with history checking"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            # Check password history
            if current_user.check_password_history(form.new_password.data):
                flash('You cannot reuse a recent password. Please choose a different password.', 'error')
                return redirect(url_for('auth.change_password'))
            
            current_user.set_password(form.new_password.data)
            db.session.commit()
            log_security_event(f'Password changed: {current_user.username}')
            flash('Your password has been changed successfully!', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Current password is incorrect.', 'error')
            log_security_event(f'Failed password change attempt: {current_user.username}', success=False)
    
    return render_template('change_password.html', form=form)

# =============================================================================
# SECURITY SETTINGS AND 2FA ROUTES
# =============================================================================

@auth.route('/security')
@login_required
def security_settings():
    """Enhanced security settings page with 2FA management"""
    two_fa = current_user.two_factor_auth
    
    # Check Google account connection status
    google_connected = current_user.can_use_google_services()
    
    # Check if user needs to reconnect Google (expired tokens, etc.)
    needs_google_reconnect = False
    if current_user.google_access_token and not google_connected:
        needs_google_reconnect = True
    
    log_security_event(f'Security settings accessed: {current_user.username}')
    
    return render_template('auth/security_settings.html', 
                         two_fa=two_fa,
                         google_connected=google_connected,
                         needs_google_reconnect=needs_google_reconnect)

@auth.route('/security/connect-google')
@login_required
def connect_google():
    """Redirect to Google OAuth to connect account for 2FA"""
    log_security_event(f'User requested Google account connection: {current_user.username}')
    return redirect(url_for('simple_google_auth.google_login'))

@auth.route('/security/test-2fa')
@login_required
def test_2fa():
    """Test 2FA email sending using universal EmailService"""
    # Generate test code
    test_code = f"{secrets.randbelow(1000000):06d}"
    
    # Use the universal EmailService to send test email
    if EmailService.send_2fa_code_email(current_user, test_code):
        flash(f'✅ Test email sent successfully! (Test code: {test_code})', 'success')
        log_security_event(f'2FA test email sent: {current_user.username}')
    else:
        flash('❌ Failed to send test email. Please check your email configuration or contact support.', 'error')
        log_security_event(f'2FA test email failed: {current_user.username}', success=False)
    
    return redirect(url_for('auth.security_settings'))

# =============================================================================
# PASSWORD RESET ROUTES (Enhanced)
# =============================================================================

# Add this to your auth.py file - enhanced forgot_password route

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request - works for ALL users"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Generate reset token
            token = user.generate_reset_token()
            db.session.commit()
            
            # Generate reset URL
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            
            # Send email to ALL users (not just Google users)
            email_sent = EmailService.send_password_reset_email(user, reset_url)
            
            if email_sent:
                flash('A password reset link has been sent to your email address.', 'success')
                log_security_event(f'Password reset email sent: {user.email}')
            else:
                # Fallback: log the URL for development/debugging
                current_app.logger.info(f'Password reset requested for {user.email}. Reset URL: {reset_url}')
                flash('Password reset requested, but there was an issue sending the email. Please contact support or check the console logs for the reset link.', 'warning')
                log_security_event(f'Password reset requested (email failed): {user.email}')
        else:
            # Always show same message for security (even if user doesn't exist)
            # This prevents email enumeration attacks
            pass
        
        # Always show success message for security
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html', form=form)


def send_password_reset_email(user, reset_url):
    """Send password reset email using Gmail API"""
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import base64
        import requests
        
        # Create email message
        message = MIMEMultipart()
        message['To'] = user.email
        message['From'] = user.email  # Send from user's own email
        message['Subject'] = 'SilverSage - Password Reset Request'
        
        # Email body
        body = f"""
        Hello {user.first_name or user.username},
        
        You requested a password reset for your SilverSage account.
        
        Click the link below to reset your password:
        {reset_url}
        
        This link will expire in 1 hour for security reasons.
        
        If you didn't request this reset, please ignore this email or contact support if you have concerns.
        
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
            from google_auth import refresh_google_token
            if refresh_google_token(user):
                # Retry with new token
                headers['Authorization'] = f'Bearer {user.google_access_token}'
                response = requests.post(gmail_url, headers=headers, json=data, timeout=15)
            else:
                return False
        
        if response.status_code == 200:
            current_app.logger.info(f"Password reset email sent successfully to {user.email}")
            return True
        else:
            current_app.logger.error(f"Gmail API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error sending password reset email: {str(e)}")
        return False

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset with token - enhanced"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    # Find user with this token
    user = User.query.filter_by(password_reset_token=token).first()
    if not user or not user.verify_reset_token(token):
        flash('Invalid or expired reset token. Please request a new password reset.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Check password history
        if user.check_password_history(form.password.data):
            flash('You cannot reuse a recent password. Please choose a different password.', 'error')
            return render_template('auth/reset_password.html', form=form)
        
        # Set new password
        user.set_password(form.password.data)
        user.password_reset_token = None
        user.password_reset_expiry = None
        user.failed_login_attempts = 0  # Reset failed attempts
        user.account_locked_until = None  # Unlock account if locked
        db.session.commit()
        
        log_security_event(f'Password reset completed: {user.username}')
        flash('Your password has been reset successfully! You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)


# Email configuration test route (for debugging)
@auth.route('/test-email-config')
@login_required
def test_email_config():
    """Test email configuration - admin only"""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))
    
    success, message = EmailService.test_email_configuration()
    
    if success:
        flash(f'✅ Email Test: {message}', 'success')
    else:
        flash(f'❌ Email Test: {message}', 'error')
    
    return redirect(url_for('auth.security_settings'))

# =============================================================================
# ADMIN-RELATED AUTH FUNCTIONS
# =============================================================================

def admin_required(f):
    """Decorator to require admin privileges"""
    from functools import wraps
    
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You need administrator privileges to access this page.', 'error')
            log_security_event('Unauthorized admin access attempt', success=False)
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@auth.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit errors"""
    log_security_event('Rate limit exceeded', success=False)
    return render_template('error.html', 
                         error_code=429, 
                         error_message='Too many requests. Please wait a moment and try again.'), 429

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def send_security_notification(user, event_type, details=None):
    """Send security notification to user (placeholder for future email integration)"""
    # This would integrate with your email system
    current_app.logger.info(f'Security notification for {user.email}: {event_type}')
    if details:
        current_app.logger.info(f'Details: {details}')

def check_account_security(user):
    """Check various security aspects of user account"""
    security_score = 100
    recommendations = []
    
    # Check password age
    if user.updated_at and (datetime.utcnow() - user.updated_at).days > 90:
        security_score -= 20
        recommendations.append("Consider changing your password (it's over 90 days old)")
    
    # Check 2FA status
    if not user.has_2fa_enabled():
        security_score -= 30
        recommendations.append("Enable two-factor authentication for better security")
    
    # Check Google account connection
    if not user.can_use_google_services():
        security_score -= 10
        recommendations.append("Connect your Google account for enhanced features")
    
    # Check failed login attempts
    if user.failed_login_attempts > 0:
        security_score -= (user.failed_login_attempts * 5)
        recommendations.append(f"There have been {user.failed_login_attempts} failed login attempts")
    
    return {
        'score': max(security_score, 0),
        'recommendations': recommendations
    }

# =============================================================================
# ACCOUNT MANAGEMENT ROUTES
# =============================================================================

@auth.route('/account-security')
@login_required
def account_security():
    """Show account security analysis"""
    security_analysis = check_account_security(current_user)
    
    return render_template('auth/account_security.html', 
                         analysis=security_analysis)

@auth.route('/download-account-data')
@login_required
def download_account_data():
    """Allow user to download their account data (GDPR compliance)"""
    import json
    from flask import Response
    
    # Prepare user data
    user_data = {
        'username': current_user.username,
        'email': current_user.email,
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'age': current_user.age,
        'contact_number': current_user.contact_number,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
        'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
        'is_admin': current_user.is_admin,
        'is_volunteer': current_user.is_volunteer,
        'two_factor_enabled': current_user.has_2fa_enabled(),
        'google_account_connected': current_user.can_use_google_services()
    }
    
    # Create JSON response
    json_data = json.dumps(user_data, indent=2)
    
    response = Response(
        json_data,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename=silversage_account_data_{current_user.username}.json'
        }
    )
    
    log_security_event(f'Account data downloaded: {current_user.username}')
    
    return response

# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

@auth.before_app_request
def load_logged_in_user():
    """Load user on each request and check session validity"""
    if current_user.is_authenticated:
        # Update last activity
        current_user.last_login = datetime.utcnow()
        
        # Check if account is still active
        if not current_user.is_active:
            logout_user()
            flash('Your account has been deactivated. Please contact support.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check for suspicious activity (optional)
        # This could include IP changes, unusual login times, etc.
        
        try:
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f'Error updating user activity: {str(e)}')
            db.session.rollback()

# =============================================================================
# DEVELOPMENT/DEBUG ROUTES (Remove in production)
# =============================================================================

@auth.route('/debug/user-info')
@login_required
def debug_user_info():
    """Debug route to show user information (development only)"""
    if not current_app.debug:
        return "Debug routes only available in debug mode", 403
    
    user_info = {
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'is_admin': current_user.is_admin,
        'is_active': current_user.is_active,
        'has_2fa': current_user.has_2fa_enabled(),
        'google_connected': current_user.can_use_google_services(),
        'last_login': str(current_user.last_login),
        'failed_attempts': current_user.failed_login_attempts
    }
    
    return f"<pre>{json.dumps(user_info, indent=2)}</pre>"

# Import json for debug route
import json