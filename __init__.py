# Updated main.py - Enhanced with Google OAuth debugging
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from sqlalchemy import text, inspect
from models import db, User
from auth import auth
from admin import admin
from google_auth import simple_google_auth  # Fixed Google auth import
from security import add_security_headers
from config import Config
import os
import logging

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # ENHANCED: Print configuration status on startup
    google_oauth_ok = Config.print_config_status()
    
    if not google_oauth_ok:
        logger.warning("⚠️ Google OAuth configuration issues detected!")
        logger.warning("⚠️ Google login features may not work properly.")
        logger.warning("⚠️ Please check your .env file and follow the setup guide.")
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from events import events
    from forum import forum
    from volunteer import volunteer
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(simple_google_auth, url_prefix='')  # Fixed Google auth
    app.register_blueprint(admin, url_prefix='')
    app.register_blueprint(events, url_prefix='/events')
    app.register_blueprint(forum, url_prefix='/forum')
    app.register_blueprint(volunteer, url_prefix='/volunteer')
    
    # Add security headers to all responses
    app.after_request(add_security_headers)
    
    # Create upload folder if it doesn't exist
    upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        # Create default profile picture (skip if Pillow not available)
        default_pic_path = os.path.join(upload_folder, 'default.png')
        if not os.path.exists(default_pic_path):
            try:
                from PIL import Image, ImageDraw
                img = Image.new('RGB', (200, 200), color='lightgray')
                d = ImageDraw.Draw(img)
                d.text((50, 90), "No Image", fill='gray')
                img.save(default_pic_path)
            except ImportError:
                logger.warning("Pillow not available - skipping default profile picture")
            except Exception as e:
                logger.warning(f"Could not create default profile picture: {e}")
    
    # Routes
    @app.route('/')
    def index():
        """Landing page - show to all visitors first"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        else:
            return render_template('landing.html')
    
    @app.route('/home')
    def home():
        """Home page for authenticated users"""
        if not current_user.is_authenticated:
            return redirect(url_for('index'))
        return render_template('home.html')


@app.route('/faq')
def faq_page():
    """FAQ page with accessibility support"""
    return render_template('faq.html')

    @app.route('/test-db')
    def test_db():
        """Test database connection and show useful info"""
        try:
            # Test basic connection
            with db.engine.connect() as connection:
                result = connection.execute(text('SELECT 1'))
            
            # Get table information
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Try to get user count if table exists
            user_count = "N/A"
            if 'users' in existing_tables:
                try:
                    user_count = User.query.count()
                except:
                    user_count = "Table exists but different schema"
            
            return f"""
            <html>
            <head>
                <title>Database Test</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .success {{ color: green; }}
                    .info {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
                    .warning {{ color: orange; }}
                </style>
            </head>
            <body>
                <h2 class="success">✅ Database Connection Successful!</h2>
                <div class="info">
                    <p><strong>Database:</strong> {app.config['MYSQL_DATABASE']}</p>
                    <p><strong>Host:</strong> {app.config['MYSQL_HOST']}</p>
                    <p><strong>User:</strong> {app.config['MYSQL_USER']}</p>
                    <p><strong>Existing tables:</strong> {', '.join(existing_tables)}</p>
                    <p><strong>User count:</strong> {user_count}</p>
                </div>
                
                <h3>Google OAuth Status:</h3>
                <div class="info">
                    <p><strong>Client ID:</strong> {'✅ Set' if app.config.get('GOOGLE_CLIENT_ID') else '❌ Not set'}</p>
                    <p><strong>Client Secret:</strong> {'✅ Set' if app.config.get('GOOGLE_CLIENT_SECRET') else '❌ Not set'}</p>
                    <p><strong>Debug Route:</strong> <a href="/auth/google/debug">Check Google OAuth Debug</a></p>
                </div>
                
                <h3>Next Steps:</h3>
                <ol>
                    <li>If you see existing tables (users, posts, test_table), you're connected to the right database!</li>
                    <li>If 'users' table has a different schema, you may need to either:
                        <ul>
                            <li>Drop the existing tables (if they're test data)</li>
                            <li>Create a new database for this app</li>
                        </ul>
                    </li>
                    <li>If Google OAuth shows ❌, follow the Google OAuth Setup Guide</li>
                    <li>Visit <a href="/">/</a> to start using the app</li>
                </ol>
                
                <p class="warning"><strong>Note:</strong> Remove this route in production!</p>
            </body>
            </html>
            """
        except Exception as e:
            return f"""
            <html>
            <head><title>Database Error</title></head>
            <body>
                <h2 style="color: red;">❌ Database Connection Error</h2>
                <p><strong>Error:</strong> {str(e)}</p>
                <p><strong>Config:</strong></p>
                <ul>
                    <li>Host: {app.config.get('MYSQL_HOST', 'Not set')}</li>
                    <li>Database: {app.config.get('MYSQL_DATABASE', 'Not set')}</li>
                    <li>User: {app.config.get('MYSQL_USER', 'Not set')}</li>
                </ul>
                <p>Check your .env file and make sure the MySQL container is running.</p>
            </body>
            </html>
            """

    @app.route('/dashboard')
    @login_required
    def dashboard():
        if current_user.is_admin:
            return redirect(url_for('admin.admin_dashboard'))
        return render_template('dashboard.html')
    
    @app.route('/settings')
    @login_required
    def general_settings():
        """General settings placeholder"""
        return render_template('settings.html')
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', error_code=404, 
                             error_message='Page not found'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', error_code=500, 
                             error_message='Internal server error'), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template('error.html', error_code=429, 
                             error_message='Too many requests. Please wait a moment and try again.'), 429
    
    # Database initialization with Google OAuth status logging
    with app.app_context():
        try:
            # Test connection first
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            logger.info("✅ Database connection successful!")
            
            # Simple table creation
            db.create_all()
            
            # Create admin user if doesn't exist
            admin_user = User.query.filter_by(email='admin@silversage.com').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@silversage.com',
                    is_admin=True
                )
                admin_user.set_password('Admin@123')
                db.session.add(admin_user)
                db.session.commit()
                logger.info("✅ Admin user created!")
            
            logger.info("✅ Database initialized!")
                    
        except Exception as e:
            logger.error(f"❌ Database initialization error: {str(e)}")
            logger.warning("The app will still run, but database features won't work.")
    
    return app

# Create app instance for WSGI
app = create_app()
UPLOAD_FOLDER = app.config["UPLOAD_FOLDER"]

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Starting SilverSage Flask Application")
    print("="*60)
    print(f"📍 Database: {app.config.get('MYSQL_DATABASE')}")
    print(f"📍 Host: {app.config.get('MYSQL_HOST')}")
    print(f"📍 User: {app.config.get('MYSQL_USER')}")
    
    # Enhanced Google OAuth status display
    google_client_id = app.config.get('GOOGLE_CLIENT_ID')
    google_client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    
    if google_client_id and google_client_secret:
        print(f"✅ Google OAuth: Properly configured")
        print(f"   Client ID: {google_client_id[:20]}...")
    else:
        print(f"❌ Google OAuth: Not configured")
        if not google_client_id:
            print("   Missing: GOOGLE_CLIENT_ID")
        if not google_client_secret:
            print("   Missing: GOOGLE_CLIENT_SECRET")
        print("   🔧 Follow the Google OAuth Setup Guide to fix this")
    
    print("="*60)
    print("\n✅ Available URLs:")
    print("✅ Landing page: https://localhost:5000")
    print("✅ Login page: https://localhost:5000/auth/login")
    print("✅ Database test: https://localhost:5000/test-db")
    print("✅ Google OAuth debug: https://localhost:5000/auth/google/debug")
    print("✅ Admin login: admin@silversage.com / Admin@123")
    print("="*60)
    
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=False,
        ssl_context=("ssl/cert.pem", "ssl/key.pem")
    )
