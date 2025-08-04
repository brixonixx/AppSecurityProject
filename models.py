# Updated models.py - Add Google OAuth and 2FA support
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
import hashlib
import os
import secrets
import uuid

db = SQLAlchemy()

user_event_association = db.Table(
    "user_event_association",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("event_id", db.Integer, db.ForeignKey("events.event_id"), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    age = db.Column(db.Integer)
    contact_number = db.Column(db.String(20))
    profile_picture = db.Column(db.String(200), default='default.png')
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_volunteer = db.Column(db.Boolean, default=False)
    
    # Google OAuth fields
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    google_access_token = db.Column(db.Text, nullable=True)
    google_refresh_token = db.Column(db.Text, nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Volunteer-specific fields
    volunteer_approved = db.Column(db.Boolean, default=False)
    volunteer_approved_at = db.Column(db.DateTime)
    volunteer_approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    volunteer_bio = db.Column(db.Text)
    volunteer_skills = db.Column(db.Text)
    volunteer_availability = db.Column(db.String(200))
    volunteer_applied_at = db.Column(db.DateTime)
    
    # Security features
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_failed_login = db.Column(db.DateTime)
    account_locked_until = db.Column(db.DateTime)
    password_reset_token = db.Column(db.String(100))
    password_reset_expiry = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    password_history = db.relationship('PasswordHistory', backref='user', lazy='dynamic')
    approved_volunteers = db.relationship('User', 
                                        foreign_keys=[volunteer_approved_by],
                                        remote_side=[id],
                                        backref='volunteer_approver')
    events = db.relationship("Event", secondary=user_event_association, back_populates="participants", lazy="dynamic")
    two_factor_auth = db.relationship('TwoFactorAuth', backref='user', uselist=False)
    
    def set_password(self, password):
        """Enhanced password hashing with SHA-256 and salt"""
        salt = os.urandom(32)
        pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                      password.encode('utf-8'), 
                                      salt, 
                                      100000)
        self.password_hash = (salt + pwdhash).hex()
        
        if self.id:
            history = PasswordHistory(
                user_id=self.id,
                password_hash=self.password_hash
            )
            db.session.add(history)
    
    def check_password(self, password):
        """Verify password against hash with brute force protection"""
        if self.account_locked_until and self.account_locked_until > datetime.utcnow():
            return False
        
        try:
            stored = bytes.fromhex(self.password_hash)
            salt = stored[:32]
            stored_hash = stored[32:]
            pwdhash = hashlib.pbkdf2_hmac('sha256',
                                          password.encode('utf-8'),
                                          salt,
                                          100000)
            
            if pwdhash == stored_hash:
                self.failed_login_attempts = 0
                self.last_login = datetime.utcnow()
                return True
            else:
                self.failed_login_attempts += 1
                self.last_failed_login = datetime.utcnow()
                
                if self.failed_login_attempts >= 5:
                    self.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
                
                return False
        except:
            return False
    
    def check_password_history(self, password):
        """Check if password was used recently"""
        recent_passwords = self.password_history.order_by(
            PasswordHistory.created_at.desc()
        ).limit(5).all()
        
        for old_password in recent_passwords:
            try:
                stored = bytes.fromhex(old_password.password_hash)
                salt = stored[:32]
                stored_hash = stored[32:]
                pwdhash = hashlib.pbkdf2_hmac('sha256',
                                              password.encode('utf-8'),
                                              salt,
                                              100000)
                if pwdhash == stored_hash:
                    return True
            except:
                continue
        
        return False
    
    def generate_reset_token(self):
        """Generate a secure password reset token"""
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_expiry = datetime.utcnow() + timedelta(hours=1)
        return self.password_reset_token
    
    def verify_reset_token(self, token):
        """Verify if reset token is valid"""
        if not self.password_reset_token or not self.password_reset_expiry:
            return False
        
        if self.password_reset_token != token:
            return False
        
        if self.password_reset_expiry < datetime.utcnow():
            return False
        
        return True
    
    def has_2fa_enabled(self):
        """Check if user has 2FA enabled"""
        return self.two_factor_auth and self.two_factor_auth.is_enabled
    
    def can_use_google_services(self):
        """Check if user can use Google services (Gmail API)"""
        return bool(self.google_access_token and self.google_refresh_token)
    
    # ... (rest of your existing methods remain the same)
    def apply_as_volunteer(self, bio=None, skills=None, availability=None):
        """Apply to become a volunteer"""
        self.is_volunteer = True
        self.volunteer_approved = False
        self.volunteer_applied_at = datetime.utcnow()
        self.volunteer_bio = bio
        self.volunteer_skills = skills
        self.volunteer_availability = availability
    
    def approve_volunteer(self, approved_by_admin_id):
        """Approve volunteer application (admin only)"""
        self.volunteer_approved = True
        self.volunteer_approved_at = datetime.utcnow()
        self.volunteer_approved_by = approved_by_admin_id
    
    def revoke_volunteer(self):
        """Revoke volunteer status"""
        self.is_volunteer = False
        self.volunteer_approved = False
        self.volunteer_approved_at = None
        self.volunteer_approved_by = None
    
    @property
    def volunteer_status(self):
        """Get volunteer status as string"""
        if not self.is_volunteer:
            return "Not a volunteer"
        elif self.volunteer_approved:
            return "Approved volunteer"
        else:
            return "Pending approval"
    
    @property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

class TwoFactorAuth(db.Model):
    """Two-factor authentication settings"""
    __tablename__ = 'two_factor_auth'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    is_enabled = db.Column(db.Boolean, default=False)
    backup_codes = db.Column(db.Text)  # Comma-separated backup codes
    temp_code = db.Column(db.String(10))  # Temporary verification code
    temp_code_expires = db.Column(db.DateTime)  # When temp code expires
    last_used = db.Column(db.DateTime)  # Last time 2FA was used
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_backup_code_valid(self, code):
        """Check if provided code is a valid backup code"""
        if not self.backup_codes:
            return False
        
        codes = self.backup_codes.split(',')
        if code in codes:
            # Remove used code
            codes.remove(code)
            self.backup_codes = ','.join(codes)
            self.last_used = datetime.utcnow()
            return True
        return False
    
    def verify_temp_code(self, code):
        """Verify temporary 2FA code"""
        if (self.temp_code == code and 
            self.temp_code_expires and 
            self.temp_code_expires > datetime.utcnow()):
            self.last_used = datetime.utcnow()
            return True
        return False

# Keep all your existing models below (PasswordHistory, AuditLog, etc.)
class PasswordHistory(db.Model):
    """Track password history to prevent reuse"""
    __tablename__ = 'password_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    """Security audit logging"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=True)
    details = db.Column(db.Text)
    
    user = db.relationship('User', backref='audit_logs')

class VolunteerEvent(db.Model):
    """Track volunteer events and activities"""
    __tablename__ = 'volunteer_events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    max_volunteers = db.Column(db.Integer, default=10)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    creator = db.relationship('User', backref='created_events')

class VolunteerRegistration(db.Model):
    """Track volunteer registrations for events"""
    __tablename__ = 'volunteer_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('volunteer_events.id'), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='registered')
    notes = db.Column(db.Text)
    
    volunteer = db.relationship('User', backref='volunteer_registrations')
    event = db.relationship('VolunteerEvent', backref='registrations')

class Event(db.Model):
    __tablename__ = "events"
    event_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    image_file = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    participants = db.relationship("User", secondary=user_event_association, back_populates="events", lazy="dynamic")
    
    def __repr__(self):
        return f"<Event event_id={self.event_id} title={self.title} creator_id={self.user_id} created_at={self.created_at}>"
    
    def to_dict(self):
        return {
            "event_id": self.event_id,
            "title": self.title,
            "description": self.description,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "image_file": self.image_file
        }

class FileReference(db.Model):
    __tablename__ = "uploads"
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    uuid_filename = db.Column(db.String(255), nullable=False)
    
    def __repr__(self):
        return f"<File id={self.id} filename={self.uuid_filename}>"
    
    def generate_secure_filename(self, file_hash):
        return str(uuid.uuid4()).replace("-", "")
    
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    
    # Relationship to comments
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')
    
    @property
    def comment_count(self):
        return len(self.comments)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class VolunteerRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requester = db.Column(db.String(80), nullable=False)
    claimed_by = db.Column(db.String(80), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)