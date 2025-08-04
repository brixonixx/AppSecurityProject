# forum.py - Forum routes and functionality
from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from flask_login import login_required, current_user
from models import *
import logging

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

forum = Blueprint('forum', __name__)

### ------------------ FORUM ROUTES ------------------- ###

@forum.route("/")
def list_posts():
    try:
        posts = Post.query.order_by(Post.id.desc()).all()
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when trying to retrieve posts: {e}")
        flash("An error occurred when trying to retrieve posts", "danger")
        posts = []
    
    return render_template('forum.html', posts=posts)

@forum.route("/post/<int:post_id>")
def view_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when trying to retrieve post {post_id}: {e}")
        flash("An error occurred when trying to retrieve the post", "danger")
        return redirect(url_for('forum.list_posts'))
    
    return render_template('post_detail.html', post=post, comments=comments)

@forum.route("/new", methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            content = request.form.get('content')
            
            if not title or not content:
                flash("Title and content are required", "warning")
                return render_template('new_post.html')
            
            author = current_user.username  # Using current_user instead of session
            post = Post(title=title, content=content, author=author)
            db.session.add(post)
            db.session.commit()
            flash("Post created successfully!", "success")
            return redirect(url_for('forum.list_posts'))
            
        except Exception as e:
            db.session.rollback()
            logging.exception(f"An exception occurred when creating a new post: {e}")
            flash("An error occurred when creating the post", "danger")

    return render_template('new_post.html')



@forum.route("/delete/<int:post_id>", methods=['POST'])
@login_required
def delete_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)

        # Ensure only the author can delete
        if post.author != current_user.username:
            flash("You are not authorized to delete this post.", "danger")
            return redirect(url_for('forum.list_posts'))

        db.session.delete(post)
        db.session.commit()
        flash("Post deleted successfully!", "success")
        
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when deleting post {post_id}: {e}")
        flash("An error occurred when deleting the post", "danger")

    return redirect(url_for('forum.list_posts'))

### ------------------ COMMENT ROUTES ------------------- ###

@forum.route("/post/<int:post_id>/comment", methods=['POST'])
@login_required
def add_comment(post_id):
    try:
        post = Post.query.get_or_404(post_id)
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
            
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when adding comment to post {post_id}: {e}")
        flash("An error occurred when adding the comment", "danger")

    return redirect(url_for('forum.view_post', post_id=post_id))

@forum.route("/comment/delete/<int:comment_id>", methods=['POST'])
@login_required
def delete_comment(comment_id):
    try:
        comment = Comment.query.get_or_404(comment_id)
        post_id = comment.post_id

        # Ensure only the comment author can delete
        if comment.author != current_user.username:
            flash("You are not authorized to delete this comment.", "danger")
            return redirect(url_for('forum.view_post', post_id=post_id))

        db.session.delete(comment)
        db.session.commit()
        flash("Comment deleted successfully!", "success")
        
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when deleting comment {comment_id}: {e}")
        flash("An error occurred when deleting the comment", "danger")

    return redirect(url_for('forum.view_post', post_id=post_id))