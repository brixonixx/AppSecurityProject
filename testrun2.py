# testrun2.py - Extended with Community Forum, Volunteer Requests, and Scheduler

from flask import Flask, request, redirect, url_for, render_template, session, flash
from wtforms import Form, StringField, TextAreaField, IntegerField, validators
from wtforms.validators import NumberRange, DataRequired, Regexp
import shelve
import uuid


app = Flask(__name__)
app.secret_key = 'your_secret_key'

### ------------------ EXISTING CLASSES (UNCHANGED) ------------------- ###
# Points, User, Reward, Delivery, ConfirmDeliveryForm, etc.
# (keep your existing ones)

### ------------------ NEW CLASSES FOR FEATURES ------------------- ###
class Post:
    def __init__(self, post_id, title, content, author):
        self.post_id = post_id
        self.title = title
        self.content = content
        self.author = author

class VolunteerRequest:
    def __init__(self, request_id, title, description, requester, claimed_by=None):
        self.request_id = request_id
        self.title = title
        self.description = description
        self.requester = requester
        self.claimed_by = claimed_by


### ------------------ FORUM ROUTES ------------------- ###
@app.route('/forum')
def forum():
    with shelve.open('forum.db', 'c') as db:
        posts = db.get('posts', [])
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
        post_id = str(uuid.uuid4())
        new_post = Post(post_id, title, content, author)

        with shelve.open('forum.db', 'c') as db:
            posts = db.get('posts', [])
            posts.append(new_post)
            db['posts'] = posts

        flash("Post created successfully!", "success")
        return redirect(url_for('forum'))
    return render_template('new_post.html')


### ------------------ VOLUNTEER ROUTES ------------------- ###
@app.route('/volunteer')
def view_volunteers():
    with shelve.open('volunteers.db', 'c') as db:
        requests = db.get('requests', [])
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
        request_id = str(uuid.uuid4())
        vr = VolunteerRequest(request_id, title, description, requester)

        with shelve.open('volunteers.db', 'c') as db:
            requests = db.get('requests', [])
            requests.append(vr)
            db['requests'] = requests

        flash("Support request posted!", "success")
        return redirect(url_for('view_volunteers'))
    return render_template('new_volunteer.html')

@app.route('/volunteer/claim/<request_id>')
def claim_volunteer_request(request_id):
    if 'username' not in session:
        flash("Login required", "warning")
        return redirect(url_for('login'))

    with shelve.open('volunteers.db', 'c') as db:
        requests = db.get('requests', [])
        for r in requests:
            if r.request_id == request_id and r.claimed_by is None:
                r.claimed_by = session['username']
                break
        db['requests'] = requests

    flash("You have claimed this request!", "info")
    return redirect(url_for('view_volunteers'))

### ------------------ EXISTING ROUTES REMAIN HERE ------------------- ###
# Keep your existing routes like /login, /home, /points, /admin, etc.
# Don’t delete anything from the original file – just add the above code

### ------------------ TEMPLATES NEEDED ------------------- ###
# forum.html
# new_post.html
# volunteer.html
# new_volunteer.html



@app.route('/calendar')
def calendar_page():
    return render_template('calendar.html')

@app.route('/')
def index():
    return redirect(url_for('calendar_page'))

print("smd")

if __name__ == '__main__':

    app.run(debug=True)