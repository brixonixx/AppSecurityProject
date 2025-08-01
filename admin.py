from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, AuditLog
from forms import RegistrationForm, ProfileForm

# Create the admin blueprint
admin = Blueprint('admin', __name__)

# Import security functions with error handling
try:
    from security import log_security_event, sanitize_input
except ImportError:
    # Fallback if security.py has issues
    def log_security_event(action, success=True, details=None):
        pass
    
    def sanitize_input(input_string, allow_html=False):
        if not input_string:
            return input_string
        return input_string.strip()

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
    
    # Get recent audit logs
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    log_security_event('Admin dashboard accessed')
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         admin_users=admin_users,
                         locked_users=locked_users,
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
    
    # Apply filters
    if filter_by == 'active':
        query = query.filter_by(is_active=True)
    elif filter_by == 'inactive':
        query = query.filter_by(is_active=False)
    elif filter_by == 'admin':
        query = query.filter_by(is_admin=True)
    elif filter_by == 'locked':
        query = query.filter(User.failed_login_attempts >= 5)
    
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
    form = RegistrationForm()
    
    # Add admin checkbox to form dynamically
    from wtforms import BooleanField
    form.is_admin = BooleanField('Administrator')
    
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
    
    form = ProfileForm(obj=user)
    
    # Add additional fields for admin editing
    from wtforms import BooleanField, StringField
    form.username = StringField('Username')
    form.email = StringField('Email')
    form.is_admin = BooleanField('Administrator')
    form.is_active = BooleanField('Active')
    
    if request.method == 'GET':
        # Pre-populate form
        form.username.data = user.username
        form.email.data = user.email
        form.is_admin.data = user.is_admin
        form.is_active.data = user.is_active
    
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
        user.first_name = sanitize_input(form.first_name.data)
        user.last_name = sanitize_input(form.last_name.data)
        user.age = form.age.data
        user.contact_number = sanitize_input(form.contact_number.data)
        user.is_admin = form.is_admin.data
        user.is_active = form.is_active.data
        
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
    import secrets
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