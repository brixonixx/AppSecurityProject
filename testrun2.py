from flask import Flask, request, redirect, url_for, render_template, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from wtforms import Form, StringField, TextAreaField, IntegerField, validators
from datetime import datetime
import uuid
import logging
from settings import (load_user_settings, save_user_settings, get_accessibility_css,
                      validate_elderly_settings, get_language_text, INTERFACE_TEXTS)

# Import chatbot functionality
from chatbot import create_chatbot_instance, process_user_input

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Enable CORS for chatbot functionality (only for chat routes)
CORS(app, resources={"/chat*": {"origins": "*"}})

# SQLAlchemy Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Global dictionary to store chatbot instances per session
chatbot_sessions = {}


### ------------------ CHATBOT HELPER FUNCTIONS ------------------- ###

def get_or_create_chatbot(session_id: str):
    """Get existing chatbot for session or create new one"""
    if session_id not in chatbot_sessions:
        # Create new chatbot instance with elderly-friendly configuration
        chatbot_sessions[session_id] = create_chatbot_instance(
            provider='openai',  # You can change this based on your preference
            model='gpt-3.5-turbo'
        )
        logger.info(f"Created new chatbot session: {session_id}")

    return chatbot_sessions[session_id]


def cleanup_old_chatbot_sessions():
    """Clean up old chatbot sessions to prevent memory issues"""
    if len(chatbot_sessions) > 50:  # Keep max 50 active sessions
        session_ids = list(chatbot_sessions.keys())
        for session_id in session_ids[:25]:  # Remove oldest 25
            del chatbot_sessions[session_id]
        logger.info(f"Cleaned up old chatbot sessions. Current active: {len(chatbot_sessions)}")


### ------------------ MODELS ------------------- ###

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


### ------------------ CUSTOM FILTERS ------------------- ###

@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to HTML line breaks"""
    if not text:
        return text
    return text.replace('\n', '<br>')


### ------------------ ACCESSIBILITY CONTEXT ------------------- ###

@app.context_processor
def inject_accessibility_settings():
    """Make accessibility settings available in all templates"""
    user_id = session.get('username', 'anonymous')
    settings = load_user_settings(user_id)

    # Apply elderly-specific validation
    settings = validate_elderly_settings(settings)

    accessibility_css = get_accessibility_css(settings)

    return {
        'accessibility_settings': settings,
        'accessibility_css': accessibility_css,
        'get_text': lambda key: get_language_text(settings, key, INTERFACE_TEXTS)
    }


### ------------------ DUMMY LOGIN ------------------- ###
@app.before_request
def dummy_login():
    if 'username' not in session:
        session['username'] = 'testuser'


### ------------------ CHATBOT ROUTES ------------------- ###

@app.route('/chatbot')
def chatbot_page():
    """Chatbot page with accessibility support"""
    # Ensure user has session (already handled by dummy_login, but being explicit)
    if 'username' not in session:
        session['username'] = 'anonymous_user'

    return render_template('chatbot.html')


@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages from frontend - integrated with accessibility"""
    try:
        # Get JSON data from request
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'No message provided',
                'response': 'Please provide a message.'
            }), 400

        user_message = data['message']

        # Get session ID (use username for consistency with existing app)
        session_id = session.get('username', 'anonymous')

        # Clean up old sessions periodically
        cleanup_old_chatbot_sessions()

        # Get chatbot instance for this session
        chatbot = get_or_create_chatbot(session_id)

        # Get user's accessibility settings for context
        user_settings = load_user_settings(session_id)
        language = user_settings.get('language', 'en')

        # Add language context to the message if needed
        if language == 'zh':
            # Add a note to respond in Chinese if the user prefers Chinese
            contextualized_message = f"Please respond in Chinese (中文). User message: {user_message}"
        else:
            contextualized_message = user_message

        # Process the user input
        result = process_user_input(chatbot, contextualized_message)

        # Log the interaction
        logger.info(f"Chat - User {session_id}: {user_message[:50]}...")
        if result['success']:
            logger.info(f"Chat - Bot response: {result['response'][:50]}...")
        else:
            logger.warning(f"Chat - Error: {result.get('error', 'Unknown error')}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'response': 'Sorry, I encountered an error. Please try again.'
        }), 500


@app.route('/chat/clear', methods=['POST'])
def clear_chat():
    """Clear chat history for current session"""
    try:
        session_id = session.get('username', 'anonymous')
        if session_id in chatbot_sessions:
            chatbot_sessions[session_id].clear_conversation()
            logger.info(f"Cleared chat conversation for user: {session_id}")

        return jsonify({
            'success': True,
            'message': 'Chat history cleared'
        })

    except Exception as e:
        logger.error(f"Error clearing chat: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear chat'
        }), 500


@app.route('/chat/status')
def chat_status():
    """Get chatbot status and configuration"""
    session_id = session.get('username', 'anonymous')

    # Get chatbot info if exists
    chatbot_info = {}
    if session_id in chatbot_sessions:
        chatbot = chatbot_sessions[session_id]
        chatbot_info = chatbot.get_conversation_summary()

    # Get user accessibility settings
    user_settings = load_user_settings(session_id)

    return jsonify({
        'status': 'online',
        'session_id': session_id,
        'chatbot_info': chatbot_info,
        'user_settings': user_settings,
        'active_sessions': len(chatbot_sessions),
        'timestamp': datetime.utcnow().isoformat()
    })


### ------------------ ACCESSIBILITY ROUTES ------------------- ###

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Handle accessibility settings page - simplified for elderly users"""
    user_id = session.get('username', 'anonymous')

    if request.method == 'POST':
        try:
            # Handle both form data and JSON data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()

            # Simplified settings data for elderly users
            settings_data = {
                'font_size': int(data.get('font_size', 18)),
                'language': data.get('language', 'en'),
                'theme': data.get('theme', 'light'),
            }

            # Validate settings for elderly users
            settings_data = validate_elderly_settings(settings_data)

            # Save settings
            if save_user_settings(settings_data, user_id):
                if request.is_json:
                    return jsonify({
                        'status': 'success',
                        'message': get_language_text(settings_data, 'settings_saved', INTERFACE_TEXTS)
                    })
                else:
                    flash(get_language_text(settings_data, 'settings_saved', INTERFACE_TEXTS), 'success')
                    return redirect(url_for('settings'))
            else:
                if request.is_json:
                    return jsonify({'status': 'error', 'message': 'Failed to save settings'})
                else:
                    flash('Failed to save settings. Please try again.', 'error')

        except (ValueError, KeyError) as e:
            print(f"Settings error: {e}")  # For debugging
            if request.is_json:
                return jsonify({'status': 'error', 'message': f'Invalid data: {str(e)}'})
            else:
                flash('Invalid settings data. Please check your inputs.', 'error')

    # Load current settings
    settings = load_user_settings(user_id)
    settings = validate_elderly_settings(settings)

    # For GET requests, return the settings page
    return render_template('settings.html', settings=settings)


@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    """API endpoint to get current accessibility settings"""
    user_id = session.get('username', 'anonymous')
    settings = load_user_settings(user_id)
    settings = validate_elderly_settings(settings)
    return jsonify(settings)


@app.route('/api/settings/css')
def get_settings_css():
    """API endpoint to get CSS for current accessibility settings"""
    user_id = session.get('username', 'anonymous')
    settings = load_user_settings(user_id)
    settings = validate_elderly_settings(settings)
    css = get_accessibility_css(settings)

    response = app.response_class(
        css,
        mimetype='text/css'
    )
    return response


@app.route('/api/settings/reset', methods=['POST'])
def reset_settings():
    """Reset accessibility settings to elderly-friendly defaults"""
    user_id = session.get('username', 'anonymous')

    try:
        from settings import DEFAULT_SETTINGS
        elderly_defaults = validate_elderly_settings(DEFAULT_SETTINGS.copy())

        if save_user_settings(elderly_defaults, user_id):
            return jsonify({'status': 'success', 'message': 'Settings reset to defaults'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to reset settings'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error resetting settings: {str(e)}'})


@app.route('/api/settings/test-tts', methods=['POST'])
def test_tts():
    """Test text-to-speech with current settings"""
    user_id = session.get('username', 'anonymous')
    settings = load_user_settings(user_id)

    # Get test text in user's language
    test_texts = {
        'en': 'This is a test of the voice reading feature. You can adjust the speed to your preference.',
        'zh': '这是语音朗读功能的测试。您可以根据喜好调整语速。'
    }

    language = settings.get('language', 'en')
    test_text = test_texts.get(language, test_texts['en'])

    return jsonify({
        'status': 'success',
        'text': test_text,
        'rate': settings.get('speech_rate', 1.0),
        'language': language
    })


### ------------------ FORUM ROUTES ------------------- ###

@app.route('/forum')
def forum():
    """Forum page with accessibility support"""
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('forum.html', posts=posts)


@app.route('/forum/post/<int:post_id>')
def view_post(post_id):
    """View individual post with accessibility support"""
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
    return render_template('post_detail.html', post=post, comments=comments)


@app.route('/forum/new', methods=['GET', 'POST'])
def new_post():
    """Create new forum post"""
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        if not title or not content:
            flash("Please fill in both title and content.", "warning")
            return render_template('new_post.html')

        author = session['username']
        post = Post(title=title, content=content, author=author)

        try:
            db.session.add(post)
            db.session.commit()
            flash("Post created successfully!", "success")
            return redirect(url_for('forum'))
        except Exception as e:
            db.session.rollback()
            flash("Error creating post. Please try again.", "error")
            return render_template('new_post.html')

    return render_template('new_post.html')


@app.route('/forum/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    """Edit existing forum post"""
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    post = Post.query.get_or_404(post_id)

    # Ensure only the author can edit
    if post.author != session['username']:
        flash("You are not authorized to edit this post.", "danger")
        return redirect(url_for('view_post', post_id=post_id))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        if not title or not content:
            flash("Please fill in both title and content.", "warning")
            return render_template('edit_post.html', post=post)

        post.title = title
        post.content = content

        try:
            db.session.commit()
            flash("Post updated successfully!", "success")
            return redirect(url_for('view_post', post_id=post_id))
        except Exception as e:
            db.session.rollback()
            flash("Error updating post. Please try again.", "error")

    return render_template('edit_post.html', post=post)


@app.route('/forum/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    """Delete forum post"""
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    post = Post.query.get_or_404(post_id)

    # Ensure only the author can delete
    if post.author != session['username']:
        flash("You are not authorized to delete this post.", "danger")
        return redirect(url_for('forum'))

    try:
        db.session.delete(post)
        db.session.commit()
        flash("Post deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting post. Please try again.", "error")

    return redirect(url_for('forum'))


### ------------------ COMMENT ROUTES ------------------- ###

@app.route('/forum/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    """Add comment to forum post"""
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    post = Post.query.get_or_404(post_id)
    comment_content = request.form.get('comment', '').strip()

    if comment_content:
        comment = Comment(
            content=comment_content,
            author=session['username'],
            post_id=post_id
        )
        try:
            db.session.add(comment)
            db.session.commit()
            flash("Comment added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("Error adding comment. Please try again.", "error")
    else:
        flash("Comment cannot be empty.", "warning")

    return redirect(url_for('view_post', post_id=post_id))


@app.route('/comment/delete/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    """Delete comment"""
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id

    # Ensure only the comment author can delete
    if comment.author != session['username']:
        flash("You are not authorized to delete this comment.", "danger")
        return redirect(url_for('view_post', post_id=post_id))

    try:
        db.session.delete(comment)
        db.session.commit()
        flash("Comment deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting comment. Please try again.", "error")

    return redirect(url_for('view_post', post_id=post_id))


### ------------------ VOLUNTEER ROUTES ------------------- ###

@app.route('/volunteer')
def view_volunteers():
    """View volunteer requests"""
    requests = VolunteerRequest.query.all()
    return render_template('volunteer.html', requests=requests)


@app.route('/volunteer/new', methods=['GET', 'POST'])
def new_volunteer_request():
    """Create new volunteer request"""
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()

        if not title or not description:
            flash("Please fill in both title and description.", "warning")
            return render_template('new_volunteer.html')

        requester = session['username']
        vr = VolunteerRequest(title=title, description=description, requester=requester)

        try:
            db.session.add(vr)
            db.session.commit()
            flash("Support request posted!", "success")
            return redirect(url_for('view_volunteers'))
        except Exception as e:
            db.session.rollback()
            flash("Error creating request. Please try again.", "error")

    return render_template('new_volunteer.html')


@app.route('/volunteer/claim/<int:request_id>')
def claim_volunteer_request(request_id):
    """Claim volunteer request"""
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    vr = VolunteerRequest.query.get_or_404(request_id)

    if not vr.claimed_by:
        vr.claimed_by = session['username']
        try:
            db.session.commit()
            flash("You have claimed this request!", "info")
        except Exception as e:
            db.session.rollback()
            flash("Error claiming request. Please try again.", "error")
    else:
        flash("This request has already been claimed.", "warning")

    return redirect(url_for('view_volunteers'))


### ------------------ OTHER ROUTES ------------------- ###

@app.route('/calendar')
def calendar_page():
    """Calendar page with accessibility support"""
    return render_template('calendar.html')


@app.route('/faq')
def faq_page():
    """FAQ page with accessibility support"""
    return render_template('faq.html')


@app.route('/')
def index():
    """Home page - redirect to calendar"""
    return redirect(url_for('calendar_page'))


@app.route('/help')
def help_page():
    """Help page for elderly users"""
    user_id = session.get('username', 'anonymous')
    settings = load_user_settings(user_id)

    help_content = {
        'en': {
            'title': 'Help & Support',
            'sections': [
                {
                    'title': 'Getting Started',
                    'content': 'Welcome to our community forum! This is a safe place to connect with others and get help.'
                },
                {
                    'title': 'Changing Text Size',
                    'content': 'Go to Settings to make text bigger or smaller. Move the slider until the text is comfortable to read.'
                },
                {
                    'title': 'Voice Reading',
                    'content': 'Turn on Voice Reading in Settings to have the computer read text out loud to you.'
                },
                {
                    'title': 'AI Assistant',
                    'content': 'Use our AI Assistant to get help with questions or have a friendly conversation. Click on "Chatbot" in the menu.'
                },
                {
                    'title': 'Need Help?',
                    'content': 'If you need assistance, ask in the forum, use the AI Assistant, or contact a volunteer for support.'
                }
            ]
        },
        'zh': {
            'title': '帮助与支持',
            'sections': [
                {
                    'title': '开始使用',
                    'content': '欢迎来到我们的社区论坛！这是一个安全的地方，您可以与他人联系并获得帮助。'
                },
                {
                    'title': '更改文字大小',
                    'content': '转到设置以使文字变大或变小。移动滑块直到文字阅读舒适为止。'
                },
                {
                    'title': '语音朗读',
                    'content': '在设置中开启语音朗读功能，让计算机为您朗读文字。'
                },
                {
                    'title': 'AI助手',
                    'content': '使用我们的AI助手来获得问题的帮助或进行友好的对话。点击菜单中的"聊天机器人"。'
                },
                {
                    'title': '需要帮助？',
                    'content': '如果您需要帮助，请在论坛中提问，使用AI助手，或联系志愿者寻求支持。'
                }
            ]
        }
    }

    language = settings.get('language', 'en')
    content = help_content.get(language, help_content['en'])

    return render_template('help.html', help_content=content)


### ------------------ ERROR HANDLERS ------------------- ###

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


### ------------------ MAIN ------------------- ###

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")

    print("Starting Flask app with chatbot integration...")
    print("Chatbot will be available at: http://localhost:5000/chatbot")
    print("Make sure to:")
    print("1. Install: pip install flask-cors requests")
    print("2. Create chatbot.py file with the AI logic")
    print("3. Add chatbot.html to your templates folder")
    print("4. Set OPENAI_API_KEY environment variable for full AI functionality")

    app.run(debug=True, host='0.0.0.0', port=5000)