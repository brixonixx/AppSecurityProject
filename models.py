from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
import hashlib
import os
import secrets

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Increased size for better security
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    age = db.Column(db.Integer)
    contact_number = db.Column(db.String(20))
    profile_picture = db.Column(db.String(200), default='default.png')
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Security features
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_failed_login = db.Column(db.DateTime)
    account_locked_until = db.Column(db.DateTime)
    password_reset_token = db.Column(db.String(100))
    password_reset_expiry = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Password history to prevent reuse
    password_history = db.relationship('PasswordHistory', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Enhanced password hashing with SHA-256 and salt"""
        # Generate a random salt
        salt = os.urandom(32)
        
        # Hash the password with PBKDF2-HMAC-SHA256
        pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                      password.encode('utf-8'), 
                                      salt, 
                                      100000)  # 100,000 iterations for security
        
        # Store salt + hash
        self.password_hash = (salt + pwdhash).hex()
        
        # Add to password history
        if self.id:  # Only if user already exists
            history = PasswordHistory(
                user_id=self.id,
                password_hash=self.password_hash
            )
            db.session.add(history)
    
    def check_password(self, password):
        """Verify password against hash with brute force protection"""
        # Check if account is locked
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
                # Reset failed attempts on successful login
                self.failed_login_attempts = 0
                self.last_login = datetime.utcnow()
                return True
            else:
                # Increment failed attempts
                self.failed_login_attempts += 1
                self.last_failed_login = datetime.utcnow()
                
                # Lock account after 5 failed attempts
                if self.failed_login_attempts >= 5:
                    self.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
                
                return False
        except:
            return False
    
    def check_password_history(self, password):
        """Check if password was used recently"""
        # Get last 5 passwords
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
                    return True  # Password was used before
            except:
                continue
        
        return False  # Password is new
    
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
    
    # Relationship to User
    user = db.relationship('User', backref='audit_logs')