# admin.py - Admin routes and functionality (FIXED - No Duplicates)
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from forms import EventForm
from werkzeug.utils import secure_filename
from auth import allowed_file
from config import Config
from functools import wraps
from datetime import datetime
from models import *
import os
import secrets
import logging

# Create the admin blueprint FIRST
admin = Blueprint('admin', __name__)

# Then import other modules
from models import db, User, AuditLog
from admin_forms import AdminUserCreationForm, AdminEditUserForm

# Import security functions with fallback
try:
    from security import log_security_event, sanitize_input
except ImportError:
    # Fallback functions if security.py has issues
    def log_security_event(action, success=True, details=None):
        """Fallback logging function"""
        print(f"LOG: {action} - Success: {success}")
    
    def sanitize_input(input_string, allow_html=False):
        """Fallback sanitize function"""
        if not input_string:
            return input_string
        return str(input_string).strip()

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You need administrator privileges to access this page.', 'error')
            log_security_event('Unauthorized admin access attempt', success=False)
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Utility function for lockout statistics
def get_lockout_statistics():
    """Get comprehensive lockout statistics for admin dashboard"""
    # Current locked accounts
    currently_locked = User.query.filter(
        User.account_locked_until > datetime.utcnow()
    ).count()
    
    # Accounts with failed attempts (at risk)
    at_risk_accounts = User.query.filter(
        User.failed_login_attempts.between(1, 4)
    ).count()
    
    # Accounts locked in the last 24 hours
    from datetime import timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    recently_locked = User.query.filter(
        User.account_locked_until > yesterday
    ).count()
    
    # Failed login attempts in the last hour
    last_hour = datetime.utcnow() - timedelta(hours=1)
    recent_failed_attempts = User.query.filter(
        User.last_failed_login > last_hour
    ).count()
    
    return {
        'currently_locked': currently_locked,
        'at_risk_accounts': at_risk_accounts,
        'recently_locked': recently_locked,
        'recent_failed_attempts': recent_failed_attempts
    }

@admin.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Main admin dashboard with enhanced security statistics"""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(is_admin=True).count()
    
    # Enhanced lockout statistics
    lockout_stats = get_lockout_statistics()
    
    # Volunteer statistics - check if volunteer columns exist
    try:
        total_volunteers = User.query.filter_by(is_volunteer=True).count()
        pending_volunteers = User.query.filter_by(is_volunteer=True, volunteer_approved=False).count()
        approved_volunteers = User.query.filter_by(is_volunteer=True, volunteer_approved=True).count()
    except Exception:
        # If volunteer columns don't exist yet, set to 0
        total_volunteers = 0
        pending_volunteers = 0
        approved_volunteers = 0
    
    # Get recent audit logs
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    # Security alerts
    security_alerts = []
    
    if lockout_stats['currently_locked'] > 0:
        security_alerts.append({
            'type': 'danger',
            'message': f"🔒 {lockout_stats['currently_locked']} accounts are currently locked",
            'action_url': url_for('admin.locked_users'),
            'action_text': 'View Locked Accounts'
        })
    
    if lockout_stats['at_risk_accounts'] > 5:
        security_alerts.append({
            'type': 'warning', 
            'message': f"⚠️ {lockout_stats['at_risk_accounts']} accounts have failed login attempts",
            'action_url': url_for('admin.user_list', filter='at_risk'),
            'action_text': 'View At-Risk Accounts'
        })
    
    if lockout_stats['recent_failed_attempts'] > 10:
        security_alerts.append({
            'type': 'info',
            'message': f"📊 {lockout_stats['recent_failed_attempts']} failed login attempts in the last hour",
            'action_url': url_for('admin.audit_logs'),
            'action_text': 'View Audit Logs'
        })
    
    log_security_event('Admin dashboard accessed')
    
    return render_template('admin/admin_dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         admin_users=admin_users,
                         lockout_stats=lockout_stats,
                         total_volunteers=total_volunteers,
                         pending_volunteers=pending_volunteers,
                         approved_volunteers=approved_volunteers,
                         recent_logs=recent_logs,
                         security_alerts=security_alerts)

@admin.route('/admin/users')
@admin_required
def user_list():
    """List all users with search and filter capabilities"""
    # Get query parameters
    search = request.args.get('search', '')
    filter_by = request.args.get('filter', 'all')
    page = request.args.get('page', 1, type=int)
    
    # Base query
    query = User.query
    
    # Apply search
    if search:
        search = sanitize_input(search)
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.email.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    # Apply filters - check if volunteer columns exist
    if filter_by == 'active':
        query = query.filter_by(is_active=True)
    elif filter_by == 'inactive':
        query = query.filter_by(is_active=False)
    elif filter_by == 'admin':
        query = query.filter_by(is_admin=True)
    elif filter_by == 'locked':
        query = query.filter(User.failed_login_attempts >= 5)
    elif filter_by == 'at_risk':
        query = query.filter(User.failed_login_attempts.between(1, 4))
    elif filter_by in ['volunteer', 'volunteer_pending', 'volunteer_approved']:
        try:
            if filter_by == 'volunteer':
                query = query.filter_by(is_volunteer=True)
            elif filter_by == 'volunteer_pending':
                query = query.filter_by(is_volunteer=True, volunteer_approved=False)
            elif filter_by == 'volunteer_approved':
                query = query.filter_by(is_volunteer=True, volunteer_approved=True)
        except Exception:
            # If volunteer columns don't exist, show no results
            query = query.filter(User.id == -1)
    
    # Paginate results
    users = query.paginate(page=page, per_page=20, error_out=False)
    
    log_security_event('Admin viewed user list')
    
    return render_template('admin/users.html', 
                         users=users,
                         search=search,
                         filter_by=filter_by)

@admin.route('/admin/user/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create a new user"""
    form = AdminUserCreationForm()
    
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Username or email already exists.', 'error')
            return redirect(url_for('admin.create_user'))
        
        # Create new user
        user = User(
            username=sanitize_input(form.username.data),
            email=sanitize_input(form.email.data),
            is_admin=form.is_admin.data
        )
        user.set_password(form.password.data)
        
        # Check if volunteer fields exist before setting them
        try:
            if hasattr(form, 'is_volunteer') and form.is_volunteer.data:
                user.is_volunteer = True
                if hasattr(form, 'approve_volunteer') and form.approve_volunteer.data:
                    user.volunteer_approved = True
                    user.volunteer_approved_at = datetime.utcnow()
                    user.volunteer_approved_by = current_user.id
        except Exception:
            pass  # Volunteer columns don't exist yet
        
        db.session.add(user)
        db.session.commit()
        
        log_security_event(f'Admin created user: {user.username}')
        flash(f'User {user.username} created successfully!', 'success')
        return redirect(url_for('admin.user_list'))
    
    return render_template('admin/create_user.html', form=form)

@admin.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit an existing user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent editing the last admin
    if user.is_admin and User.query.filter_by(is_admin=True).count() == 1:
        flash('Cannot modify the last administrator account.', 'error')
        return redirect(url_for('admin.user_list'))
    
    form = AdminEditUserForm()
    
    if request.method == 'GET':
        # Pre-populate form
        form.username.data = user.username
        form.email.data = user.email
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.age.data = user.age
        form.contact_number.data = user.contact_number
        form.is_admin.data = user.is_admin
        form.is_active.data = user.is_active
        
        # Set volunteer fields if they exist
        try:
            if hasattr(form, 'is_volunteer'):
                form.is_volunteer.data = getattr(user, 'is_volunteer', False)
            if hasattr(form, 'volunteer_approved'):
                form.volunteer_approved.data = getattr(user, 'volunteer_approved', False)
        except Exception:
            pass
    
    if form.validate_on_submit():
        # Check username/email uniqueness
        if form.username.data != user.username:
            if User.query.filter_by(username=form.username.data).first():
                flash('Username already taken.', 'error')
                return redirect(url_for('admin.edit_user', user_id=user_id))
        
        if form.email.data != user.email:
            if User.query.filter_by(email=form.email.data).first():
                flash('Email already in use.', 'error')
                return redirect(url_for('admin.edit_user', user_id=user_id))
        
        # Update user
        user.username = sanitize_input(form.username.data)
        user.email = sanitize_input(form.email.data)
        user.first_name = sanitize_input(form.first_name.data) if form.first_name.data else None
        user.last_name = sanitize_input(form.last_name.data) if form.last_name.data else None
        user.age = form.age.data
        user.contact_number = sanitize_input(form.contact_number.data) if form.contact_number.data else None
        user.is_admin = form.is_admin.data
        user.is_active = form.is_active.data
        
        # Update volunteer fields if they exist
        try:
            if hasattr(form, 'is_volunteer'):
                user.is_volunteer = form.is_volunteer.data
            if hasattr(form, 'volunteer_approved'):
                if form.volunteer_approved.data and not user.volunteer_approved:
                    user.volunteer_approved = True
                    user.volunteer_approved_at = datetime.utcnow()
                    user.volunteer_approved_by = current_user.id
                elif not form.volunteer_approved.data:
                    user.volunteer_approved = False
        except Exception:
            pass
        
        db.session.commit()
        
        log_security_event(f'Admin edited user: {user.username}')
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.user_list'))
    
    return render_template('admin/edit_user.html', form=form, user=user)

@admin.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.user_list'))
    
    # Prevent deleting the last admin
    if user.is_admin and User.query.filter_by(is_admin=True).count() == 1:
        flash('Cannot delete the last administrator account.', 'error')
        return redirect(url_for('admin.user_list'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    log_security_event(f'Admin deleted user: {username}')
    flash(f'User {username} deleted successfully!', 'success')
    return redirect(url_for('admin.user_list'))

@admin.route('/admin/user/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    """Reset a user's password"""
    user = User.query.get_or_404(user_id)
    
    # Generate temporary password
    temp_password = secrets.token_urlsafe(12)
    user.set_password(temp_password)
    
    # Force password change on next login
    user.password_reset_token = 'FORCE_CHANGE'
    
    db.session.commit()
    
    log_security_event(f'Admin reset password for user: {user.username}')
    
    # In production, email this to the user
    flash(f'Password reset for {user.username}. Temporary password: {temp_password}', 'info')
    return redirect(url_for('admin.edit_user', user_id=user_id))

# SINGLE UNLOCK USER ROUTE - Enhanced with detailed feedback
@admin.route('/admin/user/<int:user_id>/unlock', methods=['POST'])
@admin_required
def unlock_user(user_id):
    """Enhanced unlock user account with detailed feedback"""
    user = User.query.get_or_404(user_id)
    
    # Capture current lockout state for logging
    was_locked = user.is_account_locked()
    failed_attempts = user.failed_login_attempts
    lockout_time = user.account_locked_until
    
    if was_locked:
        time_remaining = user.get_lockout_time_remaining()
        if time_remaining:
            minutes_left = int(time_remaining.total_seconds() / 60)
            time_info = f" ({minutes_left} minutes remaining)"
        else:
            time_info = ""
    else:
        time_info = ""
    
    # Unlock the account
    user.failed_login_attempts = 0
    user.account_locked_until = None
    user.last_failed_login = None
    
    db.session.commit()
    
    # Log the admin action with detailed information
    log_security_event(
        f'Admin unlocked user account: {user.username}', 
        success=True,
        details=f'Failed attempts reset from {failed_attempts} to 0. Lockout cleared{time_info}.'
    )
    
    if was_locked:
        flash(f'✅ Account unlocked successfully! User {user.username} had {failed_attempts} failed attempts and was locked{time_info}. They can now log in immediately.', 'success')
    elif failed_attempts > 0:
        flash(f'✅ Failed login attempts reset! User {user.username} had {failed_attempts} failed attempts. Counter has been reset to 0.', 'success')
    else:
        flash(f'ℹ️ User {user.username} was not locked and had no failed attempts. No action needed.', 'info')
    
    return redirect(url_for('admin.user_list'))

@admin.route('/admin/user/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deactivating self
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('admin.user_list'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    log_security_event(f'Admin {status} user: {user.username}')
    flash(f'User {user.username} {status} successfully!', 'success')
    
    return redirect(url_for('admin.user_list'))

# NEW LOCKOUT MANAGEMENT ROUTES
@admin.route('/admin/users/locked')
@admin_required  
def locked_users():
    """View all currently locked user accounts"""
    page = request.args.get('page', 1, type=int)
    
    # Get locked users (either by failed attempts or explicit lockout time)
    locked_users_query = User.query.filter(
        db.or_(
            User.failed_login_attempts >= 5,
            User.account_locked_until > datetime.utcnow()
        )
    )
    
    locked_users = locked_users_query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate lockout info for each user
    lockout_info = {}
    for user in locked_users.items:
        info = {
            'is_locked': user.is_account_locked(),
            'failed_attempts': user.failed_login_attempts,
            'time_remaining': None,
            'lockout_reason': 'Not locked'
        }
        
        if user.is_account_locked():
            time_remaining = user.get_lockout_time_remaining()
            if time_remaining:
                info['time_remaining'] = time_remaining
                minutes = int(time_remaining.total_seconds() / 60)
                seconds = int(time_remaining.total_seconds() % 60)
                info['lockout_reason'] = f'Locked for {minutes}m {seconds}s'
            else:
                info['lockout_reason'] = 'Lock expired (needs page refresh)'
        elif user.failed_login_attempts >= 5:
            info['lockout_reason'] = f'{user.failed_login_attempts} failed attempts'
        
        lockout_info[user.id] = info
    
    total_locked = locked_users_query.count()
    
    log_security_event('Admin viewed locked users list')
    
    return render_template('admin/locked_users.html', 
                         users=locked_users,
                         lockout_info=lockout_info,
                         total_locked=total_locked)

@admin.route('/admin/users/unlock-all', methods=['POST'])
@admin_required
def unlock_all_users():
    """Unlock all currently locked user accounts (emergency function)"""
    
    # Get confirmation
    confirmation = request.form.get('confirmation', '').lower()
    if confirmation != 'unlock all accounts':
        flash('❌ Confirmation text does not match. No accounts were unlocked.', 'error')
        return redirect(url_for('admin.locked_users'))
    
    # Find all locked users
    locked_users = User.query.filter(
        db.or_(
            User.failed_login_attempts >= 5,
            User.account_locked_until > datetime.utcnow()
        )
    ).all()
    
    if not locked_users:
        flash('ℹ️ No locked accounts found.', 'info')
        return redirect(url_for('admin.locked_users'))
    
    # Unlock all accounts
    unlock_count = 0
    for user in locked_users:
        if user.failed_login_attempts > 0 or user.is_account_locked():
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.last_failed_login = None
            unlock_count += 1
    
    db.session.commit()
    
    # Log the mass unlock action
    unlocked_usernames = [user.username for user in locked_users]
    log_security_event(
        f'Admin performed mass account unlock', 
        success=True,
        details=f'Unlocked {unlock_count} accounts: {", ".join(unlocked_usernames)}'
    )
    
    flash(f'✅ Successfully unlocked {unlock_count} user accounts. All users can now log in immediately.', 'success')
    
    return redirect(url_for('admin.locked_users'))

@admin.route('/admin/audit-logs')
@admin_required
def audit_logs():
    """View security audit logs"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    action_filter = request.args.get('action', '')
    
    query = AuditLog.query
    
    if search:
        search = sanitize_input(search)
        query = query.filter(
            db.or_(
                AuditLog.action.contains(search),
                AuditLog.ip_address.contains(search),
                AuditLog.details.contains(search)
            )
        )
    
    if action_filter:
        query = query.filter_by(action=action_filter)
    
    logs = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Get unique actions for filter dropdown
    actions = db.session.query(AuditLog.action).distinct().all()
    actions = [a[0] for a in actions]
    
    return render_template('admin/audit_logs.html', 
                         logs=logs,
                         search=search,
                         action_filter=action_filter,
                         actions=actions)

@admin.route('/admin/export-users')
@admin_required
def export_users():
    """Export user list to CSV"""
    import csv
    from io import StringIO
    from flask import Response
    
    # Create CSV
    si = StringIO()
    writer = csv.writer(si)
    
    # Header
    writer.writerow(['ID', 'Username', 'Email', 'First Name', 'Last Name', 
                     'Admin', 'Active', 'Created At', 'Last Login'])
    
    # Data
    users = User.query.all()
    for user in users:
        writer.writerow([
            user.id,
            user.username,
            user.email,
            user.first_name or '',
            user.last_name or '',
            'Yes' if user.is_admin else 'No',
            'Yes' if user.is_active else 'No',
            user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'
        ])
    
    # Create response
    output = si.getvalue()
    response = Response(output, mimetype='text/csv')
    response.headers["Content-Disposition"] = "attachment; filename=users_export.csv"
    
    log_security_event('Admin exported user list')
    
    return response

@admin.route('/admin/forum')
@admin_required
def forum_management():
    """Forum management placeholder"""
    log_security_event('Admin accessed forum management')
    return render_template('admin/forum_management.html')

@admin.route('/admin/faq')
@admin_required
def faq_management():
    """FAQ management placeholder"""
    log_security_event('Admin accessed FAQ management')
    return render_template('admin/faq_management.html')

# Volunteer management routes
@admin.route('/admin/volunteers')
@admin_required
def volunteer_management():
    """Manage volunteers and applications"""
    try:
        # Get query parameters
        filter_by = request.args.get('filter', 'all')
        page = request.args.get('page', 1, type=int)
        
        # Base query for volunteers
        query = User.query.filter_by(is_volunteer=True)
        
        # Apply filters
        if filter_by == 'pending':
            query = query.filter_by(volunteer_approved=False)
        elif filter_by == 'approved':
            query = query.filter_by(volunteer_approved=True)
        elif filter_by == 'all':
            pass  # Show all volunteers
        
        # Paginate results
        volunteers = query.order_by(User.volunteer_applied_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        # Get statistics
        total_volunteers = User.query.filter_by(is_volunteer=True).count()
        pending_volunteers = User.query.filter_by(is_volunteer=True, volunteer_approved=False).count()
        approved_volunteers = User.query.filter_by(is_volunteer=True, volunteer_approved=True).count()
        
        log_security_event('Admin viewed volunteer management')
        
        return render_template('admin/volunteer_management.html',
                            volunteers=volunteers,
                            filter_by=filter_by,
                            total_volunteers=total_volunteers,
                            pending_volunteers=pending_volunteers,
                            approved_volunteers=approved_volunteers)
    except Exception as e:
        flash('Volunteer features are not available yet. Please run the database migration first.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

@admin.route('/admin/volunteer/<int:volunteer_id>/approve', methods=['POST'])
@admin_required
def approve_volunteer(volunteer_id):
    """Approve a volunteer application"""
    try:
        volunteer = User.query.get_or_404(volunteer_id)
        
        if not volunteer.is_volunteer:
            flash('User is not a volunteer applicant.', 'error')
            return redirect(url_for('admin.volunteer_management'))
        
        if volunteer.volunteer_approved:
            flash('Volunteer is already approved.', 'info')
            return redirect(url_for('admin.volunteer_management'))
        
        # Approve the volunteer
        volunteer.volunteer_approved = True
        volunteer.volunteer_approved_at = datetime.utcnow()
        volunteer.volunteer_approved_by = current_user.id
        db.session.commit()
        
        log_security_event(f'Admin approved volunteer: {volunteer.username}')
        flash(f'Volunteer {volunteer.username} approved successfully!', 'success')
        
        return redirect(url_for('admin.volunteer_management'))
    except Exception as e:
        flash('Volunteer features are not available yet. Please run the database migration first.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

@admin.route('/admin/volunteer/<int:volunteer_id>/revoke', methods=['POST'])
@admin_required
def revoke_volunteer(volunteer_id):
    """Revoke volunteer status"""
    try:
        volunteer = User.query.get_or_404(volunteer_id)
        
        if not volunteer.is_volunteer:
            flash('User is not a volunteer.', 'error')
            return redirect(url_for('admin.volunteer_management'))
        
        # Revoke volunteer status
        volunteer.is_volunteer = False
        volunteer.volunteer_approved = False
        volunteer.volunteer_approved_at = None
        volunteer.volunteer_approved_by = None
        db.session.commit()
        
        log_security_event(f'Admin revoked volunteer status: {volunteer.username}')
        flash(f'Volunteer status revoked for {volunteer.username}.', 'warning')
        
        return redirect(url_for('admin.volunteer_management'))
    except Exception as e:
        flash('Volunteer features are not available yet. Please run the database migration first.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

@admin.route('/admin/volunteer/<int:volunteer_id>/view')
@admin_required
def view_volunteer(volunteer_id):
    """View volunteer details"""
    try:
        volunteer = User.query.get_or_404(volunteer_id)
        
        if not volunteer.is_volunteer:
            flash('User is not a volunteer.', 'error')
            return redirect(url_for('admin.volunteer_management'))
        
        log_security_event(f'Admin viewed volunteer details: {volunteer.username}')
        
        return render_template('admin/volunteer_details.html', volunteer=volunteer)
    except Exception as e:
        flash('Volunteer features are not available yet. Please run the database migration first.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))


@admin.route("/admin/events", methods=["GET", "POST"])
@admin_required
def event_management():
    """Enhanced event management with comprehensive input sanitization and security"""
    log_security_event('Admin accessed event management')

    form = EventForm()
    events = []
    user_id = current_user.id

    if not user_id:
        logging.warning("Something is wrong, no user ID found for this user.")
        log_security_event('Event management accessed without valid user ID', success=False)
        flash("Unexpected error occurred", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    try:
        if request.method == "POST" and form.validate_on_submit():
            # Sanitize form inputs
            title = sanitize_input(form.title.data.strip()) if form.title.data else ""
            description = sanitize_input(form.description.data.strip()) if form.description.data else ""

            # Validate sanitized inputs
            validation_errors = []

            # Title validation
            if not title:
                validation_errors.append("Event title is required")
            elif len(title) > 200:
                validation_errors.append("Event title is too long (maximum 200 characters)")
            elif len(title) < 3:
                validation_errors.append("Event title is too short (minimum 3 characters)")

            # Description validation
            if not description:
                validation_errors.append("Event description is required")
            elif len(description) > 2000:
                validation_errors.append("Event description is too long (maximum 2000 characters)")
            elif len(description) < 10:
                validation_errors.append("Event description is too short (minimum 10 characters)")

            # Check for potentially malicious patterns
            suspicious_patterns = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=', 'onclick=']
            for pattern in suspicious_patterns:
                if pattern.lower() in title.lower() or pattern.lower() in description.lower():
                    validation_errors.append("Input contains potentially unsafe content")
                    log_security_event(f'Admin attempted to create event with suspicious content',
                                       success=False, details=f'Pattern: {pattern}')
                    break

            if validation_errors:
                for error in validation_errors:
                    flash(error, "danger")
                return render_template("admin/event_management.html", form=form, events=events)

            # Handle file upload with enhanced security
            file = form.image_file.data
            image_file = None

            if file and file.filename:
                # Validate file
                if not allowed_file(file.filename):
                    log_security_event(f'Admin attempted to upload invalid file type: {file.filename}', success=False)
                    flash("Invalid file type. Only PNG, JPG and JPEG are allowed.", "danger")
                    return render_template("admin/event_management.html", form=form, events=events)

                # Use secure filename function from security module
                try:
                    from security import secure_filename_custom, alt_secure_filename_custom

                    # Try the enhanced secure filename function first
                    filename = alt_secure_filename_custom(file.filename)
                    if not filename:
                        # Fallback to basic secure filename
                        filename = secure_filename_custom(file.filename)
                        if not filename:
                            # Final fallback to werkzeug's secure_filename
                            filename = secure_filename(file.filename)
                            if not filename or filename == '':
                                raise ValueError("Unable to generate secure filename")

                    # Ensure upload directory exists
                    upload_dir = Config.UPLOAD_FOLDER
                    if not os.path.exists(upload_dir):
                        os.makedirs(upload_dir, mode=0o755)

                    filepath = os.path.join(upload_dir, filename)

                    # Additional security check - ensure file doesn't already exist
                    counter = 1
                    base_filename, ext = os.path.splitext(filename)
                    while os.path.exists(filepath):
                        filename = f"{base_filename}_{counter}{ext}"
                        filepath = os.path.join(upload_dir, filename)
                        counter += 1
                        if counter > 1000:  # Prevent infinite loop
                            raise ValueError("Too many file conflicts")

                    # Save file
                    file.save(filepath)

                    # Verify file was saved correctly and get file hash for integrity
                    if os.path.exists(filepath):
                        try:
                            from security import hash_file
                            file_hash = hash_file(filepath)
                            log_security_event(f'Admin uploaded event image: {filename}',
                                               success=True, details=f'Hash: {file_hash[:16]}...')
                        except:
                            pass  # Hash function failed, but file upload succeeded

                        image_file = f"/static/uploads/{filename}"
                    else:
                        raise ValueError("File was not saved successfully")

                except Exception as e:
                    logging.exception(f"Error processing uploaded file: {e}")
                    log_security_event(f'Admin file upload failed', success=False, details=str(e))
                    flash("Error processing uploaded file. Please try again.", "danger")
                    return render_template("admin/event_management.html", form=form, events=events)
            else:
                # No file uploaded - this might be okay depending on requirements
                log_security_event('Admin created event without image', success=True)

            # Create new event with sanitized data
            new_event = Event(
                title=title,  # Already sanitized
                description=description,  # Already sanitized
                user_id=user_id,
                image_file=image_file
            )

            db.session.add(new_event)
            db.session.commit()

            logging.info(f"Added new event ID {new_event.event_id}")
            log_security_event(f'Admin created event: {title}', success=True,
                               details=f'Event ID: {new_event.event_id}')
            flash("New event added successfully!", "success")
            return redirect(url_for("admin.event_management"))

        # Load and display existing events with sanitized data
        all_events = db.session.query(Event).all()
        events = []

        for event in all_events:
            event_dict = event.to_dict()
            # Sanitize event data for display
            if 'title' in event_dict and event_dict['title']:
                event_dict['title'] = sanitize_input(event_dict['title'])
            if 'description' in event_dict and event_dict['description']:
                event_dict['description'] = sanitize_input(event_dict['description'])
            events.append(event_dict)

    except Exception as e:
        logging.exception("Error occurred when managing events")
        log_security_event('Admin event management failed', success=False, details=str(e))
        db.session.rollback()
        flash(f"An error occurred when managing events.", "danger")

    if request.method == "POST" and not form.validate_on_submit():
        log_security_event('Admin event form validation failed', success=False)
        flash("Error in the submitted data. Please validate and resubmit", "danger")

    return render_template("admin/event_management.html", form=form, events=events)


@admin.route("/admin/events/delete/<event_id>", methods=["POST"])
@admin_required
def delete_event(event_id):
    """Enhanced event deletion with input validation and security logging"""
    try:
        # Sanitize and validate event_id
        try:
            event_id_int = int(event_id)
            if event_id_int <= 0:
                raise ValueError("Invalid event ID")
        except (ValueError, TypeError):
            log_security_event(f'Admin attempted to delete event with invalid ID: {event_id}', success=False)
            flash("Invalid event ID", "danger")
            return redirect(url_for("admin.event_management"))

        # Get event from database
        event = db.session.query(Event).get(event_id_int)
        if not event:
            log_security_event(f'Admin attempted to delete non-existent event: {event_id}', success=False)
            flash("Invalid event ID", "danger")
            return redirect(url_for("admin.event_management"))

        # Store event details for logging before deletion
        event_title = sanitize_input(event.title) if event.title else f"Event {event_id}"
        event_description_preview = (sanitize_input(event.description)[:50] + "...") if event.description and len(
            event.description) > 50 else sanitize_input(event.description) if event.description else "No description"

        # Check if event has registered users
        registered_users_count = len(event.users) if hasattr(event, 'users') else 0

        if registered_users_count > 0:
            log_security_event(f'Admin deleted event with {registered_users_count} registered users',
                               success=True, details=f'Event: {event_title}')
            flash(
                f"Warning: Event had {registered_users_count} registered users who have been automatically unregistered.",
                "warning")

        # Handle image file deletion if exists
        if event.image_file:
            try:
                # Extract filename from image_file path
                if event.image_file.startswith('/static/uploads/'):
                    filename = event.image_file.replace('/static/uploads/', '')
                    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)

                    if os.path.exists(filepath):
                        os.remove(filepath)
                        log_security_event(f'Admin deleted event image file: {filename}', success=True)
                    else:
                        log_security_event(f'Event image file not found for deletion: {filename}', success=False)

            except Exception as file_error:
                logging.exception(f"Error deleting event image file: {file_error}")
                log_security_event(f'Failed to delete event image file', success=False, details=str(file_error))
                # Continue with event deletion even if file deletion fails

        # Delete the event
        db.session.delete(event)
        db.session.commit()

        log_security_event(f'Admin deleted event: {event_title}', success=True,
                           details=f'ID: {event_id_int}, Users affected: {registered_users_count}')
        flash(f"Event '{event_title}' deleted successfully!", "success")

    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when deleting an event: {e}")
        log_security_event(f'Admin event deletion failed', success=False,
                           details=f'Event ID: {event_id}, Error: {str(e)}')
        flash(f"An error occurred when deleting the event", "danger")

    return redirect(url_for("admin.event_management"))


# Additional helper function for bulk event operations
@admin.route("/admin/events/delete-all", methods=["POST"])
@admin_required
def delete_all_events():
    """Delete all events with confirmation (emergency function)"""
    try:
        # Get confirmation from form
        confirmation = request.form.get('confirmation', '').strip()
        confirmation_sanitized = sanitize_input(confirmation).lower()

        if confirmation_sanitized != 'delete all events':
            log_security_event('Admin attempted bulk event deletion without proper confirmation', success=False)
            flash('Confirmation text does not match. Events were not deleted.', 'error')
            return redirect(url_for('admin.event_management'))

        # Count events and users affected before deletion
        all_events = Event.query.all()
        event_count = len(all_events)
        total_affected_users = 0

        if event_count == 0:
            flash('No events to delete.', 'info')
            return redirect(url_for('admin.event_management'))

        # Count affected users and collect event info for logging
        event_info = []
        for event in all_events:
            user_count = len(event.users) if hasattr(event, 'users') else 0
            total_affected_users += user_count
            event_title = sanitize_input(event.title) if event.title else f"Event {event.event_id}"
            event_info.append(f"{event_title} ({user_count} users)")

        # Delete all events
        Event.query.delete()
        db.session.commit()

        log_security_event(f'Admin deleted all events (count: {event_count})', success=True,
                           details=f'Events: {"; ".join(event_info[:10])}{"..." if len(event_info) > 10 else ""}. Total users affected: {total_affected_users}')

        flash(
            f'Successfully deleted all {event_count} events from the database! {total_affected_users} user registrations were removed.',
            'success')

    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when deleting all events: {e}")
        log_security_event('Admin failed to delete all events', success=False,
                           details=f'Error: {str(e)}')
        flash("An error occurred when deleting all events", "danger")

    return redirect(url_for('admin.event_management'))


# Enhanced event validation function
def validate_event_input(title, description, file=None):
    """
    Comprehensive validation for event inputs
    Returns: (is_valid, errors, sanitized_data)
    """
    errors = []
    sanitized_data = {}

    # Sanitize inputs
    title_clean = sanitize_input(title.strip()) if title else ""
    description_clean = sanitize_input(description.strip()) if description else ""

    # Title validation
    if not title_clean:
        errors.append("Event title is required")
    elif len(title_clean) < 3:
        errors.append("Event title must be at least 3 characters long")
    elif len(title_clean) > 200:
        errors.append("Event title cannot exceed 200 characters")
    else:
        sanitized_data['title'] = title_clean

    # Description validation
    if not description_clean:
        errors.append("Event description is required")
    elif len(description_clean) < 10:
        errors.append("Event description must be at least 10 characters long")
    elif len(description_clean) > 2000:
        errors.append("Event description cannot exceed 2000 characters")
    else:
        sanitized_data['description'] = description_clean

    # File validation
    if file and file.filename:
        if not allowed_file(file.filename):
            errors.append("Invalid file type. Only PNG, JPG, and JPEG files are allowed")
        else:
            # Additional file size check (if needed)
            # Note: This would require checking the file size
            sanitized_data['has_file'] = True

    # Check for suspicious content
    suspicious_patterns = [
        '<script', 'javascript:', 'vbscript:', 'data:text/html',
        'onload=', 'onerror=', 'onclick=', 'onmouseover=',
        '<?php', '<%', '<jsp:', '${', '{{',
        'eval(', 'exec(', 'system(', 'shell_exec('
    ]

    combined_text = f"{title_clean} {description_clean}".lower()
    for pattern in suspicious_patterns:
        if pattern.lower() in combined_text:
            errors.append("Input contains potentially unsafe content")
            log_security_event(f'Suspicious pattern detected in event input: {pattern}', success=False)
            break

    return (len(errors) == 0, errors, sanitized_data)

@admin.route('/admin/posts')
@admin_required
def post_management():
    """View all posts for management"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    try:
        # Base query for posts
        query = Post.query
        
        # Apply search if provided
        if search:
            search = sanitize_input(search)
            query = query.filter(
                db.or_(
                    Post.title.contains(search),
                    Post.content.contains(search),
                    Post.author.contains(search)
                )
            )
        
        # Paginate results
        posts = query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        # Get total post count
        total_posts = Post.query.count()
        
        log_security_event('Admin viewed post management')
        
        return render_template('admin/post_management.html',
                             posts=posts,
                             search=search,
                             total_posts=total_posts)
    except Exception as e:
        logging.exception(f"Error in post management: {e}")
        flash('An error occurred while loading posts.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin.route('/admin/posts/delete-all', methods=['POST'])
@admin_required
def delete_all_posts():
    """Delete all posts in the database"""
    try:
        # Get confirmation from form
        confirmation = request.form.get('confirmation', '').lower()
        
        if confirmation != 'delete all posts':
            flash('Confirmation text does not match. Posts were not deleted.', 'error')
            return redirect(url_for('admin.post_management'))
        
        # Count posts before deletion for logging
        post_count = Post.query.count()
        
        if post_count == 0:
            flash('No posts to delete.', 'info')
            return redirect(url_for('admin.post_management'))
        
        # Delete all posts
        Post.query.delete()
        db.session.commit()
        
        log_security_event(f'Admin deleted all posts (count: {post_count})', success=True, 
                          details=f'Deleted {post_count} posts from database')
        
        flash(f'Successfully deleted all {post_count} posts from the database!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when deleting all posts: {e}")
        log_security_event('Admin failed to delete all posts', success=False, 
                          details=f'Error: {str(e)}')
        flash("An error occurred when deleting all posts", "danger")
    
    return redirect(url_for('admin.post_management'))

@admin.route('/admin/posts/delete/<int:post_id>', methods=['POST'])
@admin_required
def delete_single_post(post_id):
    """Delete a single post by ID"""
    try:
        post = Post.query.get_or_404(post_id)
        post_title = post.title
        post_author = post.author
        
        db.session.delete(post)
        db.session.commit()
        
        log_security_event(f'Admin deleted post: {post_title} by {post_author}')
        flash(f'Post "{post_title}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when deleting post {post_id}: {e}")
        flash("An error occurred when deleting the post", "danger")
    
    return redirect(url_for('admin.post_management'))