# admin.py - Admin routes and functionality
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
import os
import secrets

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

@admin.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Main admin dashboard with user statistics"""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(is_admin=True).count()
    locked_users = User.query.filter(User.failed_login_attempts >= 5).count()
    
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
    
    log_security_event('Admin dashboard accessed')
    
    return render_template('admin/admin_dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         admin_users=admin_users,
                         locked_users=locked_users,
                         total_volunteers=total_volunteers,
                         pending_volunteers=pending_volunteers,
                         approved_volunteers=approved_volunteers,
                         recent_logs=recent_logs)

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

@admin.route('/admin/user/<int:user_id>/unlock', methods=['POST'])
@admin_required
def unlock_user(user_id):
    """Unlock a locked user account"""
    user = User.query.get_or_404(user_id)
    
    user.failed_login_attempts = 0
    user.account_locked_until = None
    
    db.session.commit()
    
    log_security_event(f'Admin unlocked user: {user.username}')
    flash(f'User {user.username} unlocked successfully!', 'success')
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

# Placeholder admin routes
@admin.route('/admin/events')
@admin_required
def event_management():
    """Event management placeholder"""
    log_security_event('Admin accessed event management')
    return render_template('admin/event_management.html')

@admin.route('/admin/feedback')
@admin_required
def feedback_management():
    """Feedback management placeholder"""
    log_security_event('Admin accessed feedback management')
    return render_template('admin/feedback_management.html')

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