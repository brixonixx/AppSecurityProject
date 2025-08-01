from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
import os
import secrets
from models import db, User
from forms import LoginForm, RegistrationForm, ProfileForm, ChangePasswordForm
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
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'error')
                log_security_event(f'Login attempt on deactivated account: {user.email}', success=False)
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=form.remember_me.data)
            log_security_event(f'User login: {user.username}')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            log_security_event(f'Failed login attempt for email: {form.email.data}', success=False)
    
    return render_template('login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
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