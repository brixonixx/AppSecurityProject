# testrun2.py - Complete Flask Application with Database-Centric Approach

from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from markupsafe import escape
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, TextAreaField, IntegerField, validators
from datetime import datetime, timedelta
import uuid
import os
from sqlalchemy import text
from functools import wraps
from collections import defaultdict
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# SQLAlchemy Config - Updated to match PDF requirements
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flask_user:Silvers%40ge123@ivp-silversage.duckdns.org:3306/flask_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

### ------------------ RATE LIMITING ------------------- ###

class RateLimiter:
    def __init__(self):
        # Store attempts: {ip_address: {endpoint: [(timestamp, count), ...]}}
        self.attempts = defaultdict(lambda: defaultdict(list))
        
    def is_allowed(self, ip_address, endpoint, limit, window_seconds):
        """
        Check if request is allowed based on rate limiting rules
        
        Args:
            ip_address: Client IP address
            endpoint: API endpoint being accessed
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            tuple: (is_allowed: bool, remaining_requests: int, reset_time: datetime)
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Clean old entries
        self.attempts[ip_address][endpoint] = [
            (timestamp, count) for timestamp, count in self.attempts[ip_address][endpoint]
            if timestamp > window_start
        ]
        
        # Count current requests in window
        current_count = sum(count for _, count in self.attempts[ip_address][endpoint])
        
        if current_count >= limit:
            # Find the oldest request to determine when window resets
            if self.attempts[ip_address][endpoint]:
                oldest_request = min(self.attempts[ip_address][endpoint])[0]
                reset_time = oldest_request + timedelta(seconds=window_seconds)
            else:
                reset_time = now + timedelta(seconds=window_seconds)
            return False, 0, reset_time
        
        # Add current request
        self.attempts[ip_address][endpoint].append((now, 1))
        
        remaining = limit - (current_count + 1)
        reset_time = now + timedelta(seconds=window_seconds)
        
        return True, remaining, reset_time

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(limit=10, window=60, per='ip'):
    """
    Rate limiting decorator
    
    Args:
        limit: Number of requests allowed
        window: Time window in seconds
        per: Rate limit per 'ip' or 'user' (if logged in)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Determine identifier for rate limiting
            if per == 'user':
                current_user = get_current_user()
                if current_user:
                    identifier = f"user:{current_user.id}"
                else:
                    identifier = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            else:
                identifier = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                if identifier is None:
                    identifier = 'unknown'
            
            endpoint = request.endpoint or f.__name__
            
            # Check rate limit
            allowed, remaining, reset_time = rate_limiter.is_allowed(
                identifier, endpoint, limit, window
            )
            
            if not allowed:
                # Rate limit exceeded
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Try again after {reset_time.strftime("%Y-%m-%d %H:%M:%S")} UTC',
                    'reset_time': reset_time.isoformat()
                })
                response.status_code = 429
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(int(reset_time.timestamp()))
                response.headers['Retry-After'] = str(int((reset_time - datetime.utcnow()).total_seconds()))
                
                # For HTML requests, show a user-friendly page
                if request.accept_mimetypes.accept_html:
                    flash(f"Too many requests. Please wait until {reset_time.strftime('%H:%M:%S')} UTC before trying again.", "warning")
                    return redirect(request.referrer or url_for('index'))
                
                return response
            
            # Add rate limit headers to response
            response = f(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(int(reset_time.timestamp()))
            
            return response
        return decorated_function
    return decorator

### ------------------ DATABASE HELPER FUNCTIONS ------------------- ###

def get_current_user():
    """Helper function to get current user from database"""
    if 'user_id' not in session:
        return None
    
    try:
        return db.session.query(User).get(session['user_id'])
    except Exception as e:
        # Handle case where is_volunteer column doesn't exist
        try:
            result = db.session.execute(
                text("SELECT id, username, password, email, created_at FROM user WHERE id = :user_id"),
                {"user_id": session['user_id']}
            ).first()
            
            if result:
                # Create a user-like object
                class SimpleUser:
                    def __init__(self, id, username, password, email, created_at):
                        self.id = id
                        self.username = username
                        self.password = password
                        self.email = email
                        self.created_at = created_at
                        self.is_volunteer = session.get('is_volunteer', False)
                
                return SimpleUser(*result)
            return None
        except Exception as e2:
            print(f"Error getting current user: {e2}")
            return None

def get_user_by_username(username):
    """Helper function to get user by username"""
    try:
        return db.session.query(User).filter(User.username == username).first()
    except Exception as e:
        # Handle case where is_volunteer column doesn't exist
        try:
            result = db.session.execute(
                text("SELECT id, username, password, email, created_at FROM user WHERE username = :username"),
                {"username": username}
            ).first()
            
            if result:
                class SimpleUser:
                    def __init__(self, id, username, password, email, created_at):
                        self.id = id
                        self.username = username
                        self.password = password
                        self.email = email
                        self.created_at = created_at
                        self.is_volunteer = username == 'testuser' or session.get('is_volunteer', False)
                
                return SimpleUser(*result)
            return None
        except Exception as e2:
            print(f"Error getting user by username: {e2}")
            return None

def get_user_by_id(user_id):
    """Helper function to get user by ID"""
    return db.session.query(User).get(user_id)

### ------------------ MODELS ------------------- ###

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_volunteer = db.Column(db.Boolean, default=False)  # Enhanced volunteer field

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'is_volunteer': self.is_volunteer
        }

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

### ------------------ CUSTOM FILTERS ------------------- ###

@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to HTML line breaks"""
    if not text:
        return text
    return text.replace('\n', '<br>')

### ------------------ AUTO LOGIN ------------------- ###

@app.before_request
def dummy_login():
    if 'user_id' not in session:
        # Try to find testuser or create one
        try:
            # First try with is_volunteer column
            testuser = db.session.query(User).filter(User.username == 'testuser').first()
            if not testuser:
                testuser = User(
                    username='testuser',
                    password='testpass',
                    email='test@example.com',
                    is_volunteer=True
                )
                db.session.add(testuser)
                db.session.commit()
        except Exception as e:
            # Handle case where is_volunteer column doesn't exist
            try:
                # Query without is_volunteer column
                result = db.session.execute(
                    text("SELECT id, username, password, email, created_at FROM user WHERE username = :username"),
                    {"username": "testuser"}
                ).first()
                
                if result:
                    session['user_id'] = result[0]
                    session['username'] = result[1]
                    session['is_volunteer'] = True  # Store in session
                    return
                else:
                    # Create testuser without is_volunteer
                    db.session.execute(
                        text("INSERT INTO user (username, password, email, created_at) VALUES (:username, :password, :email, :created_at)"),
                        {
                            "username": "testuser",
                            "password": "testpass", 
                            "email": "test@example.com",
                            "created_at": datetime.utcnow()
                        }
                    )
                    db.session.commit()
                    
                    # Get the created user
                    result = db.session.execute(
                        text("SELECT id, username FROM user WHERE username = :username"),
                        {"username": "testuser"}
                    ).first()
                    
                    session['user_id'] = result[0]
                    session['username'] = result[1]
                    session['is_volunteer'] = True
                    return
            except Exception as e2:
                print(f"Error in auto-login: {e2}")
                return
        
        session['user_id'] = testuser.id
        session['username'] = testuser.username

# ---------------- ADMIN SESSION SWITCH ---------------- #

@app.route('/set_admin')
def set_admin():
    # Find or create admin user
    admin_user = get_user_by_username('admin')
    if not admin_user:
        try:
            admin_user = User(
                username='admin',
                password='adminpass',
                email='admin@example.com',
                is_volunteer=True
            )
            db.session.add(admin_user)
            db.session.commit()
        except:
            admin_user = User(
                username='admin',
                password='adminpass',
                email='admin@example.com'
            )
            db.session.add(admin_user)
            db.session.commit()
    
    session['user_id'] = admin_user.id
    session['username'] = admin_user.username
    flash("You are now logged in as admin (development mode).", "info")
    return redirect(url_for('index'))

@app.route('/set_user')
def set_user():
    # Find testuser
    testuser = get_user_by_username('testuser')
    if testuser:
        session['user_id'] = testuser.id
        session['username'] = testuser.username
        flash("You are now logged in as normal user (development mode).", "info")
    return redirect(url_for('index'))

# ---------------- ADMIN ROUTES ---------------- #

@app.route('/admin/forum', methods=['GET', 'POST'])
def admin_forum():
    # Get current user from database
    current_user = get_current_user()
    if not current_user or current_user.username != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('forum'))

    if request.method == 'POST':
        # Delete all forum posts
        db.session.query(Comment).delete()
        db.session.query(Post).delete()
        db.session.commit()
        flash("All posts have been deleted successfully!", "success")
        return redirect(url_for('admin_forum'))

    posts = db.session.query(Post).order_by(Post.created_at.desc()).all()
    return render_template('admin_forum.html', posts=posts)

@app.route('/admin/volunteer', methods=['GET', 'POST'])
def admin_volunteer():
    # Get current user from database
    current_user = get_current_user()
    if not current_user or current_user.username != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('view_volunteers'))

    if request.method == 'POST':
        # Delete all volunteer requests
        db.session.query(VolunteerRequest).delete()
        db.session.commit()
        flash("All volunteer requests have been deleted successfully!", "success")
        return redirect(url_for('admin_volunteer'))

    requests_list = db.session.query(VolunteerRequest).all()
    return render_template('admin_volunteer_map.html', requests=requests_list)

### ------------------ FORUM ROUTES ------------------- ###

@app.route('/forum')
def forum():
    posts = db.session.query(Post).order_by(Post.id.desc()).all()
    return render_template('forum.html', posts=posts)

@app.route('/forum/post/<int:post_id>')
def view_post(post_id):
    post = db.session.query(Post).get_or_404(post_id)
    comments = db.session.query(Comment).filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
    return render_template('post_detail.html', post=post, comments=comments)

@app.route('/forum/new', methods=['GET', 'POST'])
@rate_limit(limit=5, window=300, per='user')  # 5 posts per 5 minutes per user
def new_post():
    current_user = get_current_user()
    if not current_user:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        post = Post(title=title, content=content, author=current_user.username)
        db.session.add(post)
        db.session.commit()
        flash("Post created successfully!", "success")
        return redirect(url_for('forum'))

    return render_template('new_post.html')

@app.route('/forum/edit/<int:post_id>', methods=['GET', 'POST'])
@rate_limit(limit=10, window=300, per='user')  # 10 edits per 5 minutes per user
def edit_post(post_id):
    current_user = get_current_user()
    if not current_user:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    post = db.session.query(Post).get_or_404(post_id)

    # Ensure only the author can edit
    if post.author != current_user.username:
        flash("You are not authorized to edit this post.", "danger")
        return redirect(url_for('view_post', post_id=post_id))

    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        db.session.commit()
        flash("Post updated successfully!", "success")
        return redirect(url_for('view_post', post_id=post_id))

    return render_template('edit_post.html', post=post)

@app.route('/forum/delete/<int:post_id>', methods=['POST'])
@rate_limit(limit=3, window=60, per='user')  # 3 deletions per minute per user
def delete_post(post_id):
    current_user = get_current_user()
    if not current_user:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    post = db.session.query(Post).get_or_404(post_id)

    # Ensure only the author can delete
    if post.author != current_user.username:
        flash("You are not authorized to delete this post.", "danger")
        return redirect(url_for('forum'))

    db.session.delete(post)
    db.session.commit()
    flash("Post deleted successfully!", "success")
    return redirect(url_for('forum'))

### ------------------ COMMENT ROUTES ------------------- ###

@app.route('/forum/post/<int:post_id>/comment', methods=['POST'])
@rate_limit(limit=10, window=60, per='user')  # 10 comments per minute per user
def add_comment(post_id):
    current_user = get_current_user()
    if not current_user:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    post = db.session.query(Post).get_or_404(post_id)
    comment_content = request.form.get('comment')
    
    if comment_content and comment_content.strip():
        comment = Comment(
            content=comment_content.strip(),
            author=current_user.username,
            post_id=post_id
        )
        db.session.add(comment)
        db.session.commit()
        flash("Comment added successfully!", "success")
    else:
        flash("Comment cannot be empty.", "warning")

    return redirect(url_for('view_post', post_id=post_id))

@app.route('/comment/delete/<int:comment_id>', methods=['POST'])
@rate_limit(limit=5, window=60, per='user')  # 5 comment deletions per minute per user
def delete_comment(comment_id):
    current_user = get_current_user()
    if not current_user:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    comment = db.session.query(Comment).get_or_404(comment_id)
    post_id = comment.post_id

    # Ensure only the comment author can delete
    if comment.author != current_user.username:
        flash("You are not authorized to delete this comment.", "danger")
        return redirect(url_for('view_post', post_id=post_id))

    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted successfully!", "success")
    return redirect(url_for('view_post', post_id=post_id))

### ------------------ ENHANCED VOLUNTEER ROUTES ------------------- ###

@app.route('/volunteer', methods=['GET', 'POST'])
@rate_limit(limit=3, window=300, per='user')
def volunteer():
    current_user = get_current_user()
    if not current_user:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    # Special handling for testuser - make them volunteer in database
    if current_user.username == 'testuser':
        try:
            current_user.is_volunteer = True
            db.session.commit()
        except:
            # If column doesn't exist, handle gracefully
            session['is_volunteer'] = True

    if request.method == 'POST':
        lat = request.form.get('lat', type=float)
        lng = request.form.get('lng', type=float)

        if lat is None or lng is None:
            flash("Location required", "danger")
            return redirect(url_for('volunteer'))

        vr = VolunteerRequest(
            title="Help Request",
            description="User requested help",
            requester=current_user.username,
            latitude=lat,
            longitude=lng
        )
        db.session.add(vr)
        db.session.commit()
        flash("Help request sent!", "success")
        return redirect(url_for('volunteer'))

    return render_template('volunteer.html')

@app.route('/volunteer/map')
@rate_limit(limit=5, window=300, per='ip')
def volunteer_map():
    current_user = get_current_user()
    if not current_user:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    # Check if user is volunteer in database
    is_volunteer = False
    try:
        if current_user.username == 'testuser':
            current_user.is_volunteer = True
            db.session.commit()
        is_volunteer = current_user.is_volunteer
    except:
        # Handle missing column
        is_volunteer = session.get('is_volunteer', False) or current_user.username == 'testuser'

    if is_volunteer:
        return render_template('volunteer_map.html')

    flash("You must be a registered volunteer to view this page", "danger")
    return redirect(url_for('volunteer'))

@app.route('/volunteer/go/<int:request_id>', methods=['DELETE'])
@rate_limit(limit=10, window=60, per='user')
def volunteer_go_to_request(request_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"success": False, "error": "Login required"}), 403

    # Check volunteer status from database
    is_volunteer = False
    try:
        if current_user.username == 'testuser':
            current_user.is_volunteer = True
            db.session.commit()
        is_volunteer = current_user.is_volunteer
    except:
        # Handle missing column
        is_volunteer = session.get('is_volunteer', False) or current_user.username == 'testuser'

    if not is_volunteer:
        return jsonify({"success": False, "error": "Only volunteers can do this"}), 403

    vr = db.session.query(VolunteerRequest).get(request_id)
    if not vr:
        return jsonify({"success": False, "error": "Request not found"}), 404

    db.session.delete(vr)
    db.session.commit()
    return jsonify({"success": True, "message": "Help request accepted and removed"})

@app.route('/volunteer/register', methods=['GET', 'POST'])
def register_volunteer():
    current_user = get_current_user()
    if not current_user:
        flash("Login required to register as a volunteer", "warning")
        return redirect(url_for('login'))

    # Special handling for testuser
    if current_user.username == 'testuser':
        try:
            current_user.is_volunteer = True
            db.session.commit()
        except:
            session['is_volunteer'] = True
        flash("Testuser is automatically a volunteer!", "info")
        return redirect(url_for('volunteer_map'))

    if request.method == 'POST':
        try:
            current_user.is_volunteer = True
            db.session.commit()
            flash("You are now registered as a volunteer!", "success")
        except Exception as e:
            flash("Error registering as volunteer. Please contact administrator.", "danger")
            print(f"Volunteer registration error: {e}")
        return redirect(url_for('volunteer_map'))

    return render_template('register_volunteer.html', user=current_user)

@app.route('/volunteer/new', methods=['GET', 'POST'])
@rate_limit(limit=3, window=300, per='user')
def new_volunteer_request():
    current_user = get_current_user()
    if not current_user:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    # Special handling for testuser
    if current_user.username == 'testuser':
        try:
            current_user.is_volunteer = True
            db.session.commit()
        except:
            session['is_volunteer'] = True
        flash("Testuser is automatically a volunteer!", "info")
        return redirect(url_for('volunteer_map'))

    if request.method == 'POST':
        try:
            current_user.is_volunteer = True
            db.session.commit()
            flash("You are now registered as a volunteer!", "success")
            return redirect(url_for('volunteer_map'))
        except Exception as e:
            flash("Error registering as volunteer. Please contact administrator.", "danger")
            print(f"Volunteer registration error: {e}")
            return redirect(url_for('volunteer'))

    return render_template('register_volunteer.html', user=current_user)

@app.route('/volunteer/claim/<int:request_id>')
@rate_limit(limit=10, window=60, per='user')
def claim_volunteer_request(request_id):
    current_user = get_current_user()
    if not current_user:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    vr = db.session.query(VolunteerRequest).get(request_id)
    if vr and not vr.claimed_by:
        vr.claimed_by = current_user.username
        db.session.commit()
        flash("You have claimed this request!", "info")

    return redirect(url_for('view_volunteers'))

# Legacy route compatibility
def view_volunteers():
    requests = db.session.query(VolunteerRequest).all()
    return render_template('volunteer_map.html', requests=requests)

@app.route('/volunteer/delete/<int:request_id>', methods=['POST'])
@rate_limit(limit=3, window=60, per='user')
def delete_volunteer_request(request_id):
    current_user = get_current_user()
    if not current_user:
        flash("Login required to delete your request", "warning")
        return redirect(url_for('volunteer_map'))

    vr = db.session.query(VolunteerRequest).get(request_id)
    if not vr:
        flash("Request not found", "danger")
        return redirect(url_for('volunteer_map'))

    # Only allow the original requester to delete their own request
    if vr.requester != current_user.username:
        flash("You are not authorized to delete this request", "danger")
        return redirect(url_for('volunteer_map'))

    db.session.delete(vr)
    db.session.commit()

    flash("Your help request has been deleted!", "success")
    return redirect(url_for('volunteer_map'))

@app.route('/volunteer/requests_json')
@rate_limit(limit=30, window=60, per='ip')
def volunteer_requests_json():
    current_user = get_current_user()
    
    # Check volunteer status from database
    is_volunteer = False
    if current_user:
        try:
            if current_user.username == 'testuser':
                current_user.is_volunteer = True
                db.session.commit()
            is_volunteer = current_user.is_volunteer
        except:
            # Handle missing column
            is_volunteer = session.get('is_volunteer', False) or (current_user.username == 'testuser')

    requests = db.session.query(VolunteerRequest).all()
    result = []
    for r in requests:
        result.append({
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "lat": r.latitude,
            "lng": r.longitude,
            "claimed_by": r.claimed_by,
            "is_owner": (r.requester == current_user.username if current_user else False),
            "can_go": is_volunteer
        })
    return jsonify(result)

### ------------------ CALENDAR ROUTES ------------------- ###

@app.route('/calendar')
def calendar_page():
    return render_template('calendar.html')

@app.route('/')
def index():
    return redirect(url_for('calendar_page'))

@app.route('/api/events')
def get_user_events():
    current_user = get_current_user()
    if not current_user:
        return jsonify({})

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    # Use safe mock data to prevent database errors
    # In a real application, you would query user-specific events from database
    events = {
        "2025-07-15": ["Karaoke at Ang Mo Kio CC"],
        "2025-07-23": ["Community Gardening"],
        "2025-07-28": ["Health Check-up"]
    }
    return jsonify(events)

### ------------------ AUTHENTICATION ROUTES ------------------- ###

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Query user from database
        user = get_user_by_username(username)
        if user and user.password == password:  # In production, use proper password hashing
            session['user_id'] = user.id
            session['username'] = user.username  # Keep for backward compatibility
            flash("Login successful!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials", "danger")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

### ------------------ UTILITY ROUTES ------------------- ###

@app.route('/api/rate-limit-status')
@rate_limit(limit=60, window=60, per='ip')
def rate_limit_status():
    """API endpoint to check current rate limit status"""
    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr) or 'unknown'
    current_user = get_current_user()
    user_info = current_user.username if current_user else 'anonymous'
    
    return jsonify({
        'ip': ip,
        'user': user_info,
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'Rate limit status check successful'
    })

# Database fix routes
@app.route('/fix_database')
def fix_database():
    """WARNING: This will delete all data! Only use in development."""
    if app.debug:  # Only allow in debug mode
        try:
            db.drop_all()
            db.create_all()
            
            # Create a test user
            test_user = User(
                username='testuser',
                password='testpass',
                email='test@example.com',
                is_volunteer=True
            )
            db.session.add(test_user)
            
            # Create an admin user
            admin_user = User(
                username='admin',
                password='adminpass',
                email='admin@example.com',
                is_volunteer=True
            )
            db.session.add(admin_user)
            
            db.session.commit()
            
            return "Database fixed! Test user and admin user created."
        except Exception as e:
            return f"Error: {str(e)}"
    else:
        return "Database reset only available in debug mode", 403

@app.route('/add_volunteer_column')
def add_volunteer_column():
    """Add is_volunteer column to existing database without deleting data"""
    if app.debug:
        try:
            # Try to add the column
            db.session.execute(text("ALTER TABLE user ADD COLUMN is_volunteer BOOLEAN DEFAULT FALSE"))
            db.session.commit()
            
            # Update testuser to be volunteer
            db.session.execute(text("UPDATE user SET is_volunteer = TRUE WHERE username = 'testuser'"))
            db.session.commit()
            
            return "Successfully added is_volunteer column! Testuser is now a volunteer."
        except Exception as e:
            return f"Error adding column (might already exist): {str(e)}"
    else:
        return "Column addition only available in debug mode", 403

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)