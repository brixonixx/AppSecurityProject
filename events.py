# admin.py - Admin routes and functionality
from flask import render_template, request, redirect, url_for, flash, session, jsonify, Blueprint
from flask_login import LoginManager, login_user, login_required, current_user
from werkzeug.utils import secure_filename

events = Blueprint('events', __name__)

from forms import *
from models import *
from security import log_security_event
from admin import admin_required, admin
from auth import allowed_file
from functools import wraps
from datetime import datetime
import os
import secrets
import logging

@events.route("/")
def list_events():
    try:
        event_objs = db.session.query(Event).all()
        events = [e.to_dict() for e in event_objs]
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occured when trying to retrieve events: {e}")
        flash("An exception occured when trying to retrieve events", "danger")
        events = []
    
    return render_template("events.html", events=events)

@events.route("/events/unsignup/<int:event_id>", methods=["POST"])
@login_required
def unsignup_event(event_id):
    user_id = current_user.id
    if not user_id:
        logging.warning("Something is wrong, no user ID found for this user.")
        flash("Unexpected error occured", "danger")    
        return redirect(url_for("dashboard"))
    
    try:
        user = db.session.query(User).get(user_id)
        if not user:
            logging.error(f"No user found with the ID {user_id}")
            flash("User not found. Please try again", "danger")
            return redirect(url_for("events.profile_events"))
        
        event = db.session.query(Event).get(event_id)
        if not event:
            logging.error(f"No event found with the ID {event_id}")
            flash("Event not found. Please try again", "danger")
            return redirect(url_for("events.profile_events"))
        
        if event not in user.events:
            flash("You are not signed up for that event", "warning")
        else:
            user.events.remove(event)
            db.session.commit()
            flash(f"You have successfully unregistered from the event {event.title}", "success")
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occured when trying to unregister from an event: {e}")
        flash("An error occured when unregistering", "danger")
    
    return redirect(url_for("events.profile_events"))

@events.route("/events/signup/<int:event_id>", methods=["POST"])
@login_required
def signup_event(event_id):
    user_id = current_user.id
    if not user_id:
        logging.warning("Something is wrong, no user ID found for this user.")
        flash("Unexpected error occured", "danger")    
        return redirect(url_for("dashboard"))
    
    try:        
        user = db.session.query(User).get(user_id)
        event = db.session.query(Event).get(event_id)
        
        if not user or not event:
            logging.warning(f"Attempt to access invalid user or event")
            flash("Invalid user or event", "danger")
            return redirect(url_for("events.list_events"))
        
        if event in user.events:
            flash("Cannot register for the same event multiple times", "danger")
            return redirect(url_for("events.list_events"))
        else:
            user.events.append(event)
            db.session.commit()
            flash(f"You have successfully signed up for event ({event.title})", "success")
        
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occured when trying to register from an event: {e}")
        flash("An error occured when unregistering", "danger")
    
    return redirect(url_for("events.list_events"))

@events.route("/events/profile", methods=["GET"])
@login_required
def profile_events():
    user_id = current_user.id
    if not user_id:
        logging.warning("Something is wrong, no user ID found for this user.")
        flash("Unexpected error occured", "danger")    
        return redirect(url_for("dashboard"))
    
    try:
        user = db.session.query(User).get(user_id)
        if not user:
            logging.warning("No/invalid user ID provided when querying user event history")
            flash("Please log in before attempting to retrieve event history", "danger")
            return redirect(url_for("auth.user_login"))
        signed_events = user.events
        events = [e.to_dict() for e in signed_events]
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occured when trying to retrieve user event history: {e}")
        flash("An error occured when attempting to load your event history", "danger")
        events = []
    
    return render_template("profile_events.html", events=events)
