# testrun2.py - With SQLAlchemy-based Forum and Volunteer Features + Comments

from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from markupsafe import escape
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, TextAreaField, IntegerField, validators
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLAlchemy Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

### ------------------ DUMMY LOGIN ------------------- ###
@app.before_request
def dummy_login():
    if 'username' not in session:
        session['username'] = 'testuser'

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
    return render_template('volunteer.html', requests=requests)

@app.route('/volunteer/new', methods=['GET', 'POST'])
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
def volunteer_map():
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Escape and validate input data
        request_id = request.form.get('request_id', type=int)
        lat = request.form.get('lat')
        lng = request.form.get('lng')

        if request_id is None or lat is None or lng is None:
            flash("Invalid input data.", "danger")
            return redirect(url_for('volunteer_map'))

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            flash("Invalid latitude or longitude.", "danger")
            return redirect(url_for('volunteer_map'))

        vr = VolunteerRequest.query.get(request_id)
        if not vr:
            flash("Volunteer request not found.", "danger")
            return redirect(url_for('volunteer_map'))

        if vr.claimed_by:
            flash("This request has already been claimed.", "warning")
            return redirect(url_for('volunteer_map'))

        # Claim the request for current user
        vr.claimed_by = session['username']
        # Optionally, store volunteer location if needed, e.g.
        # vr.helper_lat = lat
        # vr.helper_lng = lng
        db.session.commit()
        flash("You have successfully claimed this volunteer request!", "success")
        return redirect(url_for('volunteer_map'))

    # On GET render the page; data for markers is fetched via AJAX
    return render_template('volunteer_map.html', google_maps_api_key='YOUR_GOOGLE_MAPS_API_KEY')

@app.route('/volunteer/requests_json')
def volunteer_requests_json():
    requests = VolunteerRequest.query.all()
    data = [{
        'id': r.id,
        'title': escape(r.title),
        'description': escape(r.description),
        'lat': r.lat,
        'lng': r.lng,
        'claimed_by': r.claimed_by
    } for r in requests]
    return jsonify(data)
@app.route('/calendar')
def calendar_page():
    return render_template('calendar.html')

@app.route('/')
def index():
    return redirect(url_for('calendar_page'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)