import os
from datetime import timedelta
from dotenv import load_dotenv

# FIXED: Better .env file loading with explicit path
import sys
from pathlib import Path

# Get the directory where this config.py file is located
config_dir = Path(__file__).parent.absolute()
env_path = config_dir / '.env'

# Try to load .env file with better error handling
env_loaded = load_dotenv(env_path)
if env_loaded:
    print(f"✅ Successfully loaded .env file from: {env_path}")
else:
    print(f"⚠️ Could not load .env file from: {env_path}")
    # Try alternative locations
    alt_paths = [
        Path.cwd() / '.env',
        Path(__file__).parent.parent / '.env'
    ]
    for alt_path in alt_paths:
        if alt_path.exists():
            load_dotenv(alt_path)
            print(f"✅ Loaded .env from alternative location: {alt_path}")
            break
    else:
        print("❌ No .env file found. Please create one with your configuration.")

class Config:
    # Basic Flask config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database config - Updated for your MySQL container
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'flask_user')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'Silvers@ge123')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'flask_db')
    
    # URL encode the password if it contains special characters
    from urllib.parse import quote_plus
    encoded_password = quote_plus(MYSQL_PASSWORD)
    
    # Flask-SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}/{MYSQL_DATABASE}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # FIXED: Google OAuth configuration with validation
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    # Session config
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # File upload config
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Security config
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    @classmethod
    def validate_google_oauth(cls):
        """Validate Google OAuth configuration"""
        issues = []
        
        if not cls.GOOGLE_CLIENT_ID:
            issues.append("GOOGLE_CLIENT_ID not set in environment variables")
        elif not cls.GOOGLE_CLIENT_ID.endswith('.apps.googleusercontent.com'):
            issues.append("GOOGLE_CLIENT_ID format appears incorrect (should end with .apps.googleusercontent.com)")
        
        if not cls.GOOGLE_CLIENT_SECRET:
            issues.append("GOOGLE_CLIENT_SECRET not set in environment variables")
        elif len(cls.GOOGLE_CLIENT_SECRET) < 20:
            issues.append("GOOGLE_CLIENT_SECRET appears too short")
        
        return issues
    
    @classmethod
    def print_config_status(cls):
        """Print configuration status for debugging"""
        print("\n" + "="*60)
        print("🔧 SilverSage Configuration Status")
        print("="*60)
        
        # Database config
        print(f"📍 Database Host: {cls.MYSQL_HOST}")
        print(f"📍 Database Name: {cls.MYSQL_DATABASE}")
        print(f"📍 Database User: {cls.MYSQL_USER}")
        
        # Google OAuth config
        google_issues = cls.validate_google_oauth()
        if google_issues:
            print(f"❌ Google OAuth Issues:")
            for issue in google_issues:
                print(f"   - {issue}")
        else:
            print(f"✅ Google OAuth: Properly configured")
            print(f"   Client ID: {cls.GOOGLE_CLIENT_ID[:20]}...")
            print(f"   Client Secret: {'*' * 20}...")
        
        # File upload config
        print(f"📁 Upload Folder: {cls.UPLOAD_FOLDER}")
        print(f"📏 Max File Size: {cls.MAX_CONTENT_LENGTH // (1024*1024)}MB")
        
        print("="*60)
        
        return len(google_issues) == 0
    
    # SMTP Email Configuration for sending emails to ALL users
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('SMTP_EMAIL')  # Your Gmail address
    MAIL_PASSWORD = os.environ.get('SMTP_PASSWORD')  # Your Gmail App Password
    MAIL_DEFAULT_SENDER = os.environ.get('SMTP_EMAIL')
    
    # Admin email for system notifications
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@silversage.com')
    
    @classmethod
    def validate_email_config(cls):
        """Validate email configuration"""
        issues = []
        
        if not cls.MAIL_USERNAME:
            issues.append("SMTP_EMAIL not set in environment variables")
        elif not cls.MAIL_USERNAME.endswith('@gmail.com'):
            issues.append("SMTP_EMAIL should be a Gmail address")
        
        if not cls.MAIL_PASSWORD:
            issues.append("SMTP_PASSWORD not set in environment variables")
        elif len(cls.MAIL_PASSWORD) < 16:
            issues.append("SMTP_PASSWORD appears too short (should be Gmail App Password)")
        
        return issues
    
    @classmethod
    def print_config_status(cls):
        """Print configuration status for debugging"""
        print("\n" + "="*60)
        print("🔧 SilverSage Configuration Status")
        print("="*60)
        
        # Database config
        print(f"📍 Database Host: {cls.MYSQL_HOST}")
        print(f"📍 Database Name: {cls.MYSQL_DATABASE}")
        print(f"📍 Database User: {cls.MYSQL_USER}")
        
        # Google OAuth config
        google_issues = cls.validate_google_oauth()
        if google_issues:
            print(f"❌ Google OAuth Issues:")
            for issue in google_issues:
                print(f"   - {issue}")
        else:
            print(f"✅ Google OAuth: Properly configured")
            print(f"   Client ID: {cls.GOOGLE_CLIENT_ID[:20]}...")
            print(f"   Client Secret: {'*' * 20}...")
        
        # Email config
        email_issues = cls.validate_email_config()
        if email_issues:
            print(f"❌ Email Configuration Issues:")
            for issue in email_issues:
                print(f"   - {issue}")
        else:
            print(f"✅ SMTP Email: Properly configured")
            print(f"   Email: {cls.MAIL_USERNAME}")
            print(f"   Server: {cls.MAIL_SERVER}:{cls.MAIL_PORT}")
        
        # File upload config
        print(f"📁 Upload Folder: {cls.UPLOAD_FOLDER}")
        print(f"📏 Max File Size: {cls.MAX_CONTENT_LENGTH // (1024*1024)}MB")
        
        print("="*60)
        
        return len(google_issues) == 0 and len(email_issues) == 0