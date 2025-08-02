# testrun2.py - Updated with correct database configuration and Rate Limiting

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
app.secret_key = 'your-secret-key-here'  # Update this to match PDF

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
            if per == 'user' and 'username' in session:
                identifier = f"user:{session['username']}"
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

### ------------------ MODELS ------------------- ###

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
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

# ---------------- ADMIN SESSION SWITCH ---------------- #

@app.route('/set_admin')
def set_admin():
    session['username'] = 'admin'
    flash("You are now logged in as admin (development mode).", "info")
    return redirect(url_for('index'))

@app.route('/set_user')
def set_user():
    session['username'] = 'testuser'
    flash("You are now logged in as normal user (development mode).", "info")
    return redirect(url_for('index'))


# ---------------- ADMIN ROUTES ---------------- #

@app.route('/admin/forum', methods=['GET', 'POST'])
def admin_forum():
    # Ensure only admin can access
    if session.get('username') != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('forum'))

    if request.method == 'POST':
        # Delete all forum posts
        Comment.query.delete()
        Post.query.delete()
        db.session.commit()
        flash("All posts have been deleted successfully!", "success")
        return redirect(url_for('admin_forum'))

    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin_forum.html', posts=posts)


@app.route('/admin/volunteer', methods=['GET', 'POST'])
def admin_volunteer():
    # Ensure only admin can access
    if session.get('username') != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('view_volunteers'))

    if request.method == 'POST':
        # Delete all volunteer requests
        VolunteerRequest.query.delete()
        db.session.commit()
        flash("All volunteer requests have been deleted successfully!", "success")
        return redirect(url_for('admin_volunteer'))

    requests_list = VolunteerRequest.query.all()
    return render_template('admin_volunteer_map.html', requests=requests_list)


### ------------------ FORUM ROUTES ------------------- ###

@app.route('/forum')
def forum():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('forum.html', posts=posts)

@app.route('/forum/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
    return render_template('post_detail.html', post=post, comments=comments)

@app.route('/forum/new', methods=['GET', 'POST'])
@rate_limit(limit=5, window=300, per='user')  # 5 posts per 5 minutes per user
def new_post():
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        author = session['username']
        post = Post(title=title, content=content, author=author)
        db.session.add(post)
        db.session.commit()
        flash("Post created successfully!", "success")
        return redirect(url_for('forum'))

    return render_template('new_post.html')

@app.route('/forum/edit/<int:post_id>', methods=['GET', 'POST'])
@rate_limit(limit=10, window=300, per='user')  # 10 edits per 5 minutes per user
def edit_post(post_id):
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    post = Post.query.get_or_404(post_id)

    # Ensure only the author can edit
    if post.author != session['username']:
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
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    post = Post.query.get_or_404(post_id)

    # Ensure only the author can delete
    if post.author != session['username']:
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
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    post = Post.query.get_or_404(post_id)
    comment_content = request.form.get('comment')
    
    if comment_content and comment_content.strip():
        comment = Comment(
            content=comment_content.strip(),
            author=session['username'],
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
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id

    # Ensure only the comment author can delete
    if comment.author != session['username']:
        flash("You are not authorized to delete this comment.", "danger")
        return redirect(url_for('view_post', post_id=post_id))

    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted successfully!", "success")
    return redirect(url_for('view_post', post_id=post_id))

### ------------------ VOLUNTEER ROUTES ------------------- ###

@app.route('/volunteer')
def view_volunteers():
    requests = VolunteerRequest.query.all()
    return render_template('volunteer_map.html', requests=requests)

@app.route('/volunteer/new', methods=['GET', 'POST'])
@rate_limit(limit=3, window=300, per='user')  # 3 volunteer requests per 5 minutes per user
def new_volunteer_request():
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        requester = session['username']
        vr = VolunteerRequest(title=title, description=description, requester=requester)
        db.session.add(vr)
        db.session.commit()
        flash("Support request posted!", "success")
        return redirect(url_for('view_volunteers'))

    return render_template('new_volunteer.html')

@app.route('/volunteer/claim/<int:request_id>')
@rate_limit(limit=10, window=60, per='user')  # 10 claims per minute per user
def claim_volunteer_request(request_id):
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    vr = VolunteerRequest.query.get(request_id)
    if vr and not vr.claimed_by:
        vr.claimed_by = session['username']
        db.session.commit()
        flash("You have claimed this request!", "info")

    return redirect(url_for('view_volunteers'))

@app.route('/volunteer/map', methods=['GET', 'POST'])
@rate_limit(limit=5, window=300, per='ip')  # 5 map requests per 5 minutes per IP
def volunteer_map():
    if request.method == 'POST':
        lat = request.form.get('lat', type=float)
        lng = request.form.get('lng', type=float)
        username = session.get('username', 'anonymous')

        if lat is None or lng is None:
            flash("Location required", "danger")
            return redirect(url_for('volunteer_map'))

        vr = VolunteerRequest(
            title="Help Request",
            description="User requested help",
            requester=username,
            latitude=lat,
            longitude=lng
        )
        db.session.add(vr)
        db.session.commit()

        flash("Help request sent!", "success")
        return redirect(url_for('volunteer_map'))

    return render_template('volunteer_map.html')

@app.route('/volunteer/delete/<int:request_id>', methods=['POST'])
@rate_limit(limit=3, window=60, per='user')  # 3 deletions per minute per user
def delete_volunteer_request(request_id):
    if 'username' not in session:
        flash("Login required to delete your request", "warning")
        return redirect(url_for('volunteer_map'))

    vr = VolunteerRequest.query.get(request_id)
    if not vr:
        flash("Request not found", "danger")
        return redirect(url_for('volunteer_map'))

    # Only allow the original requester to delete their own request
    if vr.requester != session['username']:
        flash("You are not authorized to delete this request", "danger")
        return redirect(url_for('volunteer_map'))

    db.session.delete(vr)
    db.session.commit()

    flash("Your help request has been deleted!", "success")
    return redirect(url_for('volunteer_map'))

@app.route('/volunteer/requests_json')
@rate_limit(limit=30, window=60, per='ip')  # 30 API calls per minute per IP
def volunteer_requests_json():
    current_user = session.get('username')
    requests = VolunteerRequest.query.all()
    result = []
    for r in requests:
        result.append({
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "lat": r.latitude,
            "lng": r.longitude,
            "claimed_by": r.claimed_by,
            "is_owner": (r.requester == current_user)
        })
    return jsonify(result)

### ------------------ CALENDAR ROUTES ------------------- ###
@app.route('/calendar')
def calendar_page():
    return render_template('calendar.html')

@app.route('/')
def index():
    return redirect(url_for('calendar_page'))



# Optional: Add a route to check rate limit status
@app.route('/api/rate-limit-status')
@rate_limit(limit=60, window=60, per='ip')  # 60 checks per minute per IP
def rate_limit_status():
    """API endpoint to check current rate limit status"""
    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr) or 'unknown'
    user = session.get('username', 'anonymous')
    
    return jsonify({
        'ip': ip,
        'user': user,
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'Rate limit status check successful'
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)