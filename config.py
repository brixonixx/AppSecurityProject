import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

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
    
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}/{MYSQL_DATABASE}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
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