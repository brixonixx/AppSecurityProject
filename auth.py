# Updated auth.py - Enhanced with Google OAuth and 2FA support
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

auth = Blueprint('auth', __name__)

def allowed_file(filename):
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
                
                # Send 2FA code
                from google_auth import send_2fa_code
                two_fa_code = secrets.randbelow(1000000)
                two_fa_code_str = f"{two_fa_code:06d}"
                
                # Update 2FA record
                two_fa = user.two_factor_auth
                two_fa.temp_code = two_fa_code_str
                two_fa.temp_code_expires = datetime.utcnow() + timedelta(minutes=10)
                db.session.commit()
                
                # Send code via Gmail if possible
                if user.can_use_google_services():
                    if send_2fa_code(user, two_fa_code_str):
                        flash('A verification code has been sent to your email.', 'info')
                        return redirect(url_for('auth.two_factor'))
                    else:
                        flash('Failed to send 2FA code. Please try again later.', 'error')
                        return redirect(url_for('auth.login'))
                else:
                    flash('2FA is enabled but email service is not available. Please contact support.', 'error')
                    return redirect(url_for('auth.login'))
            else:
                # Normal login without 2FA
                login_user(user, remember=form.remember_me.data)
                log_security_event(f'User login: {user.username}')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            log_security_event(f'Failed login attempt for email: {form.email.data}', success=False)
    
    return render_template('login.html', form=form)

@auth.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    """Handle 2FA verification"""
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
            log_security_event(f'User login with backup code: {user.username}')
            
            flash('You used a backup code. Consider generating new ones.', 'warning')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        
        else:
            flash('Invalid verification code. Please try again.', 'error')
            log_security_event(f'Failed 2FA attempt: {user.username}', success=False)
    
    return render_template('auth/two_factor.html', form=form, user=user)

@auth.route('/register', methods=['GET', 'POST'])
def register():
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
    username = current_user.username
    logout_user()
    
    # Clear any pending sessions
    session.pop('pending_user_id', None)
    session.pop('remember_me', None)
    
    log_security_event(f'User logout: {username}')
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
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

# 2FA Management Routes
@auth.route('/security', methods=['GET'])
@login_required
def security_settings():
    """Security settings page"""
    two_fa = current_user.two_factor_auth
    return render_template('auth/security_settings.html', two_fa=two_fa)

@auth.route('/enable-2fa', methods=['GET', 'POST'])
@login_required
def enable_2fa():
    """Enable 2FA - redirect to Google auth integration"""
    if current_user.has_2fa_enabled():
        flash('Two-factor authentication is already enabled.', 'info')
        return redirect(url_for('auth.security_settings'))
    
    if not current_user.can_use_google_services():
        flash('You need to link your Google account first to enable 2FA.', 'warning')
        return redirect(url_for('google_auth.google_login'))
    
    # Redirect to Google auth blueprint for 2FA setup
    return redirect(url_for('google_auth.enable_2fa'))

@auth.route('/disable-2fa', methods=['GET', 'POST'])
@login_required
def disable_2fa():
    """Disable 2FA"""
    if not current_user.has_2fa_enabled():
        flash('Two-factor authentication is not enabled.', 'info')
        return redirect(url_for('auth.security_settings'))
    
    form = Disable2FAForm()
    if form.validate_on_submit():
        if current_user.check_password(form.password.data):
            # Redirect to Google auth blueprint for 2FA disable
            return redirect(url_for('google_auth.disable_2fa'))
        else:
            flash('Incorrect password.', 'error')
    
    return render_template('auth/disable_2fa.html', form=form)

# Import datetime at the top
from datetime import datetime, timedelta