from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from sqlalchemy import text, inspect
from models import db, User
from auth import auth
from admin import admin  # Import admin blueprint
from security import add_security_headers
from config import Config
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
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
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin, url_prefix='')  # Admin routes at root level
    
    # Add security headers to all responses
    app.after_request(add_security_headers)
    
    # Create upload folder if it doesn't exist
    upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        # Create default profile picture
        default_pic_path = os.path.join(upload_folder, 'default.png')
        if not os.path.exists(default_pic_path):
            try:
                from PIL import Image, ImageDraw
                img = Image.new('RGB', (200, 200), color='lightgray')
                d = ImageDraw.Draw(img)
                d.text((50, 90), "No Image", fill='gray')
                img.save(default_pic_path)
            except:
                logger.warning("Could not create default profile picture")
    
    # Routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth.login'))
    
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
                
                <h3>Next Steps:</h3>
                <ol>
                    <li>If you see existing tables (users, posts, test_table), you're connected to the right database!</li>
                    <li>If 'users' table has a different schema, you may need to either:
                        <ul>
                            <li>Drop the existing tables (if they're test data)</li>
                            <li>Create a new database for this app</li>
                        </ul>
                    </li>
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
            # Redirect admins to admin dashboard
            return redirect(url_for('admin.admin_dashboard'))
        return render_template('dashboard.html')
    
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
    
    # Create tables with safety check
    with app.app_context():
        try:
            # Test connection first
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            logger.info("✅ Database connection successful!")
            
            # Check if tables exist before creating
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Only create tables if 'users' doesn't exist
            if 'users' not in existing_tables:
                logger.info("Creating database tables...")
                db.create_all()
                
                # Create default admin user
                admin_user = User(
                    username='admin',
                    email='admin@silversage.com',
                    is_admin=True
                )
                admin_user.set_password('Admin@123')
                db.session.add(admin_user)
                db.session.commit()
                logger.info("✅ Tables created and admin user added!")
            else:
                logger.info("ℹ️ Tables already exist, skipping creation...")
                
                # Check if our User model matches the existing table
                try:
                    # Try a simple query
                    User.query.first()
                    logger.info("✅ User table schema appears compatible")
                except Exception as e:
                    logger.warning(f"⚠️ Warning: Existing 'users' table may have different schema: {str(e)}")
                    logger.warning("Consider using a different database or dropping existing tables.")
                    
        except Exception as e:
            logger.error(f"❌ Database initialization error: {str(e)}")
            logger.warning("The app will still run, but database features won't work.")
            logger.warning("Make sure your MySQL database is accessible at:")
            logger.warning(f"Host: {app.config.get('MYSQL_HOST')}")
            logger.warning(f"Database: {app.config.get('MYSQL_DATABASE')}")
    
    return app

# Create app instance for WSGI
app = create_app()

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Starting SilverSage Flask Application")
    print("="*50)
    print(f"📍 Database: {app.config.get('MYSQL_DATABASE')}")
    print(f"📍 Host: {app.config.get('MYSQL_HOST')}")
    print(f"📍 User: {app.config.get('MYSQL_USER')}")
    print("="*50)
    print("\n✅ Visit http://localhost:5000/test-db to test database connection")
    print("✅ Visit http://localhost:5000 to access the application")
    print("✅ Admin login: admin@silversage.com / Admin@123\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)