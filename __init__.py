# Updated main.py - Enhanced with Google OAuth debugging
from flask import Flask, render_template, redirect, url_for, request, session, jsonify, flash
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
from settings import *
import requests 
import json
from datetime import datetime
from security import generate_csrf_token, validate_csrf_token

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SilverSageAI:
    """AI Assistant for SilverSage - handles senior-focused conversations"""
    
    def __init__(self):
        self.system_prompt = """
        You are SageBot, an AI assistant for SilverSage, a community platform for senior citizens. 
        You are knowledgeable, patient, and empathetic. Your responses should be:
        
        - Clear and easy to understand
        - Respectful and age-appropriate
        - Focused on senior-related topics like health, technology, hobbies, family, and community
        - Helpful for navigating the SilverSage platform
        - Encouraging and positive
        
        You can help users with:
        - General questions about aging, health, and wellness
        - Technology support and explanations
        - SilverSage platform features
        - Event recommendations
        - Community engagement tips
        - Hobbies and activities for seniors
        
        Keep responses concise but warm and helpful.
        """
    
    def get_response_openai(self, user_message, conversation_history=[]):
        """Get response from OpenAI GPT"""
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if not openai_api_key:
            return "I'm sorry, but the AI service is not configured. Please contact the administrator."
        
        try:
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            }
            
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history
            for msg in conversation_history[-10:]:  # Keep last 10 messages
                messages.append(msg)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            response = requests.post("https://api.openai.com/v1/chat/completions", 
                                   headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request failed: {e}")
            return "I'm having trouble connecting to my AI service right now. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI response: {e}")
            return "I encountered an unexpected error. Please try again."
    
    def get_response_claude(self, user_message, conversation_history=[]):
        """Get response from Claude API (alternative)"""
        claude_api_key = os.environ.get('CLAUDE_API_KEY')
        if not claude_api_key:
            return "I'm sorry, but the AI service is not configured. Please contact the administrator."
        
        try:
            headers = {
                "x-api-key": claude_api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 500,
                "system": self.system_prompt,
                "messages": [{"role": "user", "content": user_message}]
            }
            
            response = requests.post("https://api.anthropic.com/v1/messages", 
                                   headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['content'][0]['text'].strip()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Claude API request failed: {e}")
            return "I'm having trouble connecting to my AI service right now. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error in Claude response: {e}")
            return "I encountered an unexpected error. Please try again."
    
    def get_response_local(self, user_message, conversation_history=[]):
        """Fallback to simple rule-based responses when no API is available"""
        user_message_lower = user_message.lower()
        
        # Simple keyword-based responses
        responses = {
            'hello': "Hello! I'm SageBot, your friendly AI assistant. How can I help you today?",
            'help': "I'm here to help! I can assist with questions about health, technology, SilverSage features, or just have a friendly chat. What would you like to know?",
            'events': "You can find upcoming events in the Events section of SilverSage. There are often social gatherings, health workshops, and hobby groups to join!",
            'forum': "The Forum is a great place to connect with other community members. You can share experiences, ask questions, or join discussions on topics you're interested in.",
            'volunteer': "Volunteering is a wonderful way to stay active and give back! Check out the Volunteer section to find opportunities that match your interests and skills.",
            'recommend': "we personally recommend morning tai chi and community garden as they promote healthy active living and also teaches valuable skills!",
            'password': "you can change your password at security settings which can be accessed from the user profile dropdown!",
            'text': "you can make your text larger by at general settings which can be accessed from the user profile dropdown!",
            'thanks': "You're very welcome! I'm always here to help whenever you need assistance.",
            'goodbye': "Goodbye for now! Feel free to chat with me anytime you visit SilverSage. Have a wonderful day!"
        }
        
        # Check for keywords
        for keyword, response in responses.items():
            if keyword in user_message_lower:
                return response
        
        # Default response
        return "I understand you're asking about that topic. While I'd love to give you a detailed answer, my advanced AI features aren't available right now. Is there something specific about SilverSage I can help you with instead?"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # ENHANCED: Print configuration status on startup
    google_oauth_ok = Config.print_config_status()
    
    if not google_oauth_ok:
        logger.warning("Warning: Google OAuth configuration issues detected!")
        logger.warning("Warning: Google login features may not work properly.")
        logger.warning("Warning: Please check your .env file and follow the setup guide.")
    
    # Initialize extensions
    db.init_app(app)

    sage_ai = SilverSageAI()
    
    # Setup login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # FIXED: This should match the blueprint route
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Global context processor for accessibility settings
    @app.context_processor
    def inject_accessibility():
        if current_user.is_authenticated:
            user_id = current_user.id
            logger.info(f"Context processor: Loading settings for user {user_id}")
            accessibility_settings = load_user_settings(user_id)
            logger.info(f"Context processor: Loaded settings: {accessibility_settings}")
            accessibility_css = get_accessibility_css(accessibility_settings)
            
            def get_text(key):
                text = get_language_text(accessibility_settings, key)
                logger.debug(f"Context processor: get_text('{key}') = '{text}' (language: {accessibility_settings.get('language', 'en')})")
                return text
                
            return {
                'accessibility_settings': accessibility_settings,
                'accessibility_css': accessibility_css,
                'get_text': get_text,
                'csrf_token': generate_csrf_token
            }
        else:
            # Default settings for non-authenticated users
            logger.info("Context processor: Using default settings for non-authenticated user")
            default_settings = DEFAULT_SETTINGS.copy()
            accessibility_css = get_accessibility_css(default_settings)
            
            def get_text(key):
                text = get_language_text(default_settings, key)
                logger.debug(f"Context processor: get_text('{key}') = '{text}' (default language)")
                return text
                
            return {
                'accessibility_settings': default_settings,
                'accessibility_css': accessibility_css,
                'get_text': get_text,
                'csrf_token': generate_csrf_token
            }
    
    # FIXED: Register blueprints with proper URL prefixes
    from events import events
    from forum import forum
    from volunteer import volunteer
    
    # Register auth blueprint WITHOUT /auth prefix so login is at /login
    app.register_blueprint(auth)
    
    # Register other blueprints
    app.register_blueprint(simple_google_auth)
    app.register_blueprint(admin)
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
    
    # FIXED: Consolidated CSP configuration
    @app.after_request
    def after_request(response):
        # Allow Leaflet CDN and other necessary resources
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com; "
            "connect-src 'self' https://*.tile.openstreetmap.org; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com; "
            "font-src 'self' data:"
        )
        response.headers['Content-Security-Policy'] = csp
        return response
    
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
                <h2 class="success">Database Connection Successful!</h2>
                <div class="info">
                    <p><strong>Database:</strong> {app.config['MYSQL_DATABASE']}</p>
                    <p><strong>Host:</strong> {app.config['MYSQL_HOST']}</p>
                    <p><strong>User:</strong> {app.config['MYSQL_USER']}</p>
                    <p><strong>Existing tables:</strong> {', '.join(existing_tables)}</p>
                    <p><strong>User count:</strong> {user_count}</p>
                </div>
                
                <h3>Google OAuth Status:</h3>
                <div class="info">
                    <p><strong>Client ID:</strong> {'Set' if app.config.get('GOOGLE_CLIENT_ID') else 'Not set'}</p>
                    <p><strong>Client Secret:</strong> {'Set' if app.config.get('GOOGLE_CLIENT_SECRET') else 'Not set'}</p>
                    <p><strong>Debug Route:</strong> <a href="/auth/google/debug">Check Google OAuth Debug</a></p>
                </div>
                
                <h3>Available Routes:</h3>
                <div class="info">
                    <p><a href="/">Landing Page</a></p>
                    <p><a href="/login">Login Page</a></p>
                    <p><a href="/register">Register Page</a></p>
                    <p><a href="/auth/google">Google OAuth</a></p>
                    <p><a href="/chat">AI Chatbot</a></p>
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
                    <li>If Google OAuth shows "Not set", follow the Google OAuth Setup Guide</li>
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
                <h2 style="color: red;">Database Connection Error</h2>
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
        """User dashboard - redirect admins to admin dashboard"""
        if current_user.is_admin:
            return redirect(url_for('admin.admin_dashboard'))
        return render_template('dashboard.html')
    
    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def general_settings():
        """General settings with language and accessibility support"""
        user_id = current_user.id if current_user.is_authenticated else None
        
        if request.method == 'POST':
            # Debug logging
            logger.info(f"Settings POST request from user {user_id}")
            logger.info(f"Form data: {dict(request.form)}")
            
            # Check if request is AJAX or regular form submission
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
            
            # Handle CSRF token validation - be more lenient for debugging
            csrf_token = request.form.get('csrf_token')
            logger.info(f"CSRF token received: {csrf_token}")
            
            # Temporarily skip CSRF validation for debugging
            # if not csrf_token or not validate_csrf_token(csrf_token):
            #     logger.error("CSRF token validation failed")
            #     if is_ajax:
            #         return jsonify({'status': 'error', 'message': 'Invalid CSRF token'}), 403
            #     else:
            #         flash('Invalid CSRF token', 'error')
            #         return redirect(url_for('general_settings'))
            
            # Handle settings update
            settings_data = {
                'font_size': request.form.get('font_size', 18),
                'language': request.form.get('language', 'en'),
                'theme': request.form.get('theme', 'light')
            }
            
            logger.info(f"Attempting to save settings: {settings_data}")
            
            try:
                if save_user_settings(settings_data, user_id):
                    logger.info("Settings saved successfully")
                    if is_ajax:
                        return jsonify({'status': 'success', 'message': 'Settings saved successfully!'})
                    else:
                        flash('Settings saved successfully!', 'success')
                        return redirect(url_for('general_settings'))
                else:
                    logger.error("Failed to save settings")
                    if is_ajax:
                        return jsonify({'status': 'error', 'message': 'Failed to save settings'}), 500
                    else:
                        flash('Failed to save settings', 'error')
                        return redirect(url_for('general_settings'))
            except Exception as e:
                logger.error(f"Exception while saving settings: {str(e)}")
                if is_ajax:
                    return jsonify({'status': 'error', 'message': f'Error: {str(e)}'}), 500
                else:
                    flash(f'Error saving settings: {str(e)}', 'error')
                    return redirect(url_for('general_settings'))
        
        # The context processor already provides these, so we don't need to override them
        return render_template('settings.html')

    @app.route('/debug-settings')
    @login_required 
    def debug_settings():
        """Debug route to check what settings are being loaded"""
        user_id = current_user.id
        settings = load_user_settings(user_id)
        return f"""
        <h1>Settings Debug</h1>
        <p><strong>User ID:</strong> {user_id}</p>
        <p><strong>Username:</strong> {current_user.username}</p>
        <p><strong>Settings file:</strong> user_settings/user_{user_id}.json</p>
        <p><strong>Loaded settings:</strong> {settings}</p>
        <p><strong>Language:</strong> {settings.get('language', 'NOT SET')}</p>
        <p><strong>get_text('home'):</strong> {get_language_text(settings, 'home')}</p>
        <p><strong>get_text('settings_title'):</strong> {get_language_text(settings, 'settings_title')}</p>
        <hr>
        <a href="/settings">Back to Settings</a>
        """
    

    @app.route('/chat')
    @login_required
    def chat():
        """Main chat interface"""
        return render_template('chatbot.html')

    @app.route('/api/chat', methods=['POST'])
    @login_required
    def chat_api():
        """API endpoint for chat messages"""
        try:
            data = request.get_json()
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return jsonify({'error': 'Message cannot be empty'}), 400
            
            # Get conversation history from session
            if 'chat_history' not in session:
                session['chat_history'] = []
            
            conversation_history = session['chat_history']
            
            # Try different AI services in order of preference
            ai_response = None
            
            # Try OpenAI first
            if os.environ.get('OPENAI_API_KEY'):
                ai_response = sage_ai.get_response_openai(user_message, conversation_history)
            # Try Claude if OpenAI not available
            elif os.environ.get('CLAUDE_API_KEY'):
                ai_response = sage_ai.get_response_claude(user_message, conversation_history)
            # Fallback to local responses
            else:
                ai_response = sage_ai.get_response_local(user_message, conversation_history)
            
            # Update conversation history
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Keep only last 20 messages (10 exchanges)
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            
            session['chat_history'] = conversation_history
            session.permanent = True
            
            # Log the interaction (for debugging/improvement)
            logger.info(f"Chat interaction - User: {current_user.username}, Message length: {len(user_message)}")
            
            return jsonify({
                'response': ai_response,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            return jsonify({'error': 'Sorry, I encountered an error. Please try again.'}), 500

    @app.route('/api/chat/clear', methods=['POST'])
    @login_required
    def clear_chat():
        """Clear chat history"""
        session['chat_history'] = []
        return jsonify({'success': True})

    @app.route('/api/chat/history', methods=['GET'])
    @login_required
    def chat_history():
        """Get chat history for current session"""
        history = session.get('chat_history', [])
        return jsonify({'history': history})
    


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
            logger.info("Database connection successful!")
            
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
                logger.info("Admin user created!")
            
            logger.info("Database initialized!")
                    
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            logger.warning("The app will still run, but database features won't work.")
    
    return app

# Create app instance for WSGI
app = create_app()
UPLOAD_FOLDER = app.config["UPLOAD_FOLDER"]

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Starting SilverSage Flask Application")
    print("="*60)
    print(f"Database: {app.config.get('MYSQL_DATABASE')}")
    print(f"Host: {app.config.get('MYSQL_HOST')}")
    print(f"User: {app.config.get('MYSQL_USER')}")
    
    # Enhanced Google OAuth status display
    google_client_id = app.config.get('GOOGLE_CLIENT_ID')
    google_client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    
    if google_client_id and google_client_secret:
        print(f"Google OAuth: Properly configured")
        print(f"   Client ID: {google_client_id[:20]}...")
    else:
        print(f"Google OAuth: Not configured")
        if not google_client_id:
            print("   Missing: GOOGLE_CLIENT_ID")
        if not google_client_secret:
            print("   Missing: GOOGLE_CLIENT_SECRET")
        print("   Follow the Google OAuth Setup Guide to fix this")


    
    openai_key = app.config.get('OPENAI_API_KEY')
    claude_key = app.config.get('CLAUDE_API_KEY')
    
    if openai_key:
        print(f"✅ AI Chatbot: OpenAI configured")
    elif claude_key:
        print(f"✅ AI Chatbot: Claude configured")
    else:
        print(f"⚠️ AI Chatbot: Using rule-based responses (no API keys)")
    
    print("="*60)
    print("\nAvailable URLs:")
    print("Landing page: https://localhost:5000")
    print("Login page: https://localhost:5000/login")
    print("Register page: https://localhost:5000/register")
    print("Database test: https://localhost:5000/test-db")
    print("Google OAuth debug: https://localhost:5000/auth/google/debug")
    print("✅ AI Chatbot: https://localhost:5000/chat")
    print("Admin login: admin@silversage.com / Admin@123")
    print("="*60)
    
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=False,
        ssl_context=("ssl/cert.pem", "ssl/key.pem")
    )