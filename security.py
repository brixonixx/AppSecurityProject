"""
Security utilities for the SilverSage application
Implements security best practices for elderly users
"""

import re
import os
import secrets
from functools import wraps
from flask import request, abort, current_app, session
from markupsafe import escape
from flask_login import current_user
from models import db, AuditLog, FileReference
import hashlib
import hmac
from datetime import datetime, timedelta

# Security configuration
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 30  # minutes
PASSWORD_MIN_LENGTH = 8
PASSWORD_HISTORY_COUNT = 5
SESSION_TIMEOUT = 60  # minutes

def validate_password_strength(password):
    """
    Validate password meets security requirements
    Returns: (is_valid, error_message)
    """
    errors = []
    
    # Length check
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")
    
    # Uppercase check
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Lowercase check
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Number check
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    
    # Special character check
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    # Common password check
    common_passwords = ['password', '12345678', 'qwerty', 'admin123', 'letmein']
    if password.lower() in common_passwords:
        errors.append("Password is too common. Please choose a stronger password")
    
    return (len(errors) == 0, errors)

def log_security_event(action, success=True, details=None):
    """Log security-related events for audit trail"""
    try:
        log = AuditLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent', '')[:200],
            success=success,
            details=details
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to log security event: {str(e)}")

def get_client_ip():
    """Get client IP address, handling proxies"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
    elif request.environ.get('HTTP_X_REAL_IP'):
        return request.environ.get('HTTP_X_REAL_IP')
    else:
        return request.environ.get('REMOTE_ADDR', 'unknown')

def rate_limit(max_requests=5, window_seconds=60):
    """
    Decorator to implement rate limiting
    Prevents brute force attacks
    """
    def decorator(f):
        # Simple in-memory storage (use Redis in production)
        request_counts = {}
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identifier = get_client_ip()
            now = datetime.utcnow()
            
            # Clean old entries
            request_counts[identifier] = [
                timestamp for timestamp in request_counts.get(identifier, [])
                if timestamp > now - timedelta(seconds=window_seconds)
            ]
            
            # Check rate limit
            if len(request_counts.get(identifier, [])) >= max_requests:
                log_security_event(f"Rate limit exceeded for {request.endpoint}", success=False)
                abort(429, description="Too many requests. Please try again later.")
            
            # Add current request
            request_counts.setdefault(identifier, []).append(now)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Why are you implementing your own sanitization...
def sanitize_input(input_string, allow_html=False):
    """
    Sanitize user input to prevent XSS attacks
    """
    if not input_string:
        return input_string
    
    # Remove any null bytes
    input_string = input_string.replace('\x00', '')
    
    if not allow_html:
        # Escape HTML characters
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;'
        }
        for char, escape in replacements.items():
            input_string = input_string.replace(char, escape)
    
    return input_string.strip()

def alt_sanitize_input(input_string, allow_html=False) -> str:
    """
    Sanitize user input to prevent common web attacks
    """
    if not input_string:
        return ""
    
    # Escape special characters using Flask's builtin escape function
    escaped_input = escape(input_string)
    return escaped_input.strip()

def generate_csrf_token():
    """Generate a CSRF token for form protection"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
    return session['csrf_token']

def validate_csrf_token(token):
    """Validate CSRF token"""
    return token == session.get('csrf_token')

def check_session_timeout():
    """Check if user session has timed out"""
    if current_user.is_authenticated:
        if 'last_activity' in session:
            time_since_activity = datetime.utcnow() - session['last_activity']
            if time_since_activity > timedelta(minutes=SESSION_TIMEOUT):
                return False
        session['last_activity'] = datetime.utcnow()
    return True

def secure_filename_custom(filename):
    """
    Enhanced secure filename function
    Removes potentially dangerous characters from filenames
    """
    # Remove path separators and null bytes
    filename = filename.replace('/', '').replace('\\', '').replace('\x00', '')
    
    # Keep only safe characters
    safe_chars = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    # Ensure it has a safe extension
    name, ext = os.path.splitext(safe_chars)
    if ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
        return None
    
    # Add timestamp to prevent collisions
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return f"{timestamp}_{safe_chars}"

def alt_secure_filename_custom(filename):
    valid_characters = r"[a-zA-Z0-9_-\.]+"
    try:
        # Refer to models.FileReference as well
        is_valid = re.fullmatch(valid_characters, filename)
        if not is_valid:
            # An invalid character is found in the string
            return None
        name, ext = os.path.splitext(filename)
        if ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
            return None
        
        file = FileReference(original_filename = filename)
        file.generate_secure_filename()
        db.session.add(file)
        db.session.commit()
        return file.uuid_filename
    except Exception as e:
        db.session.rollback()
        log_security_event("An error has occured when attempting to generate a secure filename", details=e)
        return None

def hash_file(filepath):
    """Generate SHA-256 hash of a file for integrity checking"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# Security headers middleware
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Updated CSP to include Leaflet marker images
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com; "
        "connect-src 'self' https://*.tile.openstreetmap.org; "
        "img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com; "
        "font-src 'self' data:"
    )
    
    return response
