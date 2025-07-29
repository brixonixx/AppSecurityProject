# testrun2.py - With SQLAlchemy-based Forum and Volunteer Features

from flask import Flask, request, redirect, url_for, render_template, session, flash
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, TextAreaField, IntegerField, validators
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

class VolunteerRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requester = db.Column(db.String(80), nullable=False)
    claimed_by = db.Column(db.String(80), nullable=True)

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