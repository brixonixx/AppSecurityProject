# events.py - Events routes and functionality with enhanced security
from flask import render_template, request, redirect, url_for, flash, session, jsonify, Blueprint
from flask_login import LoginManager, login_user, login_required, current_user
from werkzeug.utils import secure_filename

events = Blueprint('events', __name__)

from forms import *
from models import *
from admin import admin_required, admin
from auth import allowed_file
from functools import wraps
from datetime import datetime
import os
import secrets
import logging

# Import security functions with fallback
try:
    from security import log_security_event, sanitize_input, alt_sanitize_input
except ImportError:
    # Fallback functions if security.py has issues
    def log_security_event(action, success=True, details=None):
        """Fallback logging function"""
        logging.info(f"SECURITY LOG: {action} - Success: {success} - Details: {details}")


    def sanitize_input(input_string, allow_html=False):
        """Fallback sanitize function"""
        if not input_string:
            return input_string
        # Basic sanitization
        from markupsafe import escape
        return str(escape(input_string)).strip()


    def alt_sanitize_input(input_string, allow_html=False):
        """Alternative sanitize function"""
        return sanitize_input(input_string, allow_html)


@events.route("/")
def list_events():
    """List all available events with sanitized output"""
    try:
        event_objs = db.session.query(Event).all()
        events = []

        # Sanitize event data before sending to template
        for event in event_objs:
            event_dict = event.to_dict()
            # Sanitize text fields in the event dictionary
            if 'title' in event_dict and event_dict['title']:
                event_dict['title'] = sanitize_input(event_dict['title'])
            if 'description' in event_dict and event_dict['description']:
                event_dict['description'] = sanitize_input(event_dict['description'])
            events.append(event_dict)

        log_security_event('User viewed events list', success=True)

    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when trying to retrieve events: {e}")
        log_security_event('Failed to retrieve events list', success=False, details=str(e))
        flash("An exception occurred when trying to retrieve events", "danger")
        events = []

    return render_template("events.html", events=events)


@events.route("/events/unsignup/<int:event_id>", methods=["POST"])
@login_required
def unsignup_event(event_id):
    """Unregister user from an event with enhanced security logging"""
    user_id = current_user.id
    if not user_id:
        logging.warning("Something is wrong, no user ID found for this user.")
        log_security_event('Event unsignup attempted without valid user ID', success=False)
        flash("Unexpected error occurred", "danger")
        return redirect(url_for("dashboard"))

    try:
        # Validate event_id is a positive integer
        if event_id <= 0:
            log_security_event(f'Invalid event ID provided for unsignup: {event_id}', success=False)
            flash("Invalid event ID", "danger")
            return redirect(url_for("events.profile_events"))

        user = db.session.query(User).get(user_id)
        if not user:
            logging.error(f"No user found with the ID {user_id}")
            log_security_event(f'Event unsignup failed - user not found: {user_id}', success=False)
            flash("User not found. Please try again", "danger")
            return redirect(url_for("events.profile_events"))

        event = db.session.query(Event).get(event_id)
        if not event:
            logging.error(f"No event found with the ID {event_id}")
            log_security_event(f'Event unsignup failed - event not found: {event_id}', success=False)
            flash("Event not found. Please try again", "danger")
            return redirect(url_for("events.profile_events"))

        if event not in user.events:
            log_security_event(
                f'User {user.username} attempted to unsignup from event {event_id} they were not registered for',
                success=False)
            flash("You are not signed up for that event", "warning")
        else:
            event_title = sanitize_input(event.title) if event.title else f"Event {event_id}"
            user.events.remove(event)
            db.session.commit()

            log_security_event(f'User {user.username} unregistered from event: {event_title}', success=True)
            flash(f"You have successfully unregistered from the event {event_title}", "success")

    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when trying to unregister from an event: {e}")
        log_security_event(
            f'Event unsignup failed for user {current_user.username if current_user.is_authenticated else "unknown"}',
            success=False, details=str(e))
        flash("An error occurred when unregistering", "danger")

    return redirect(url_for("events.profile_events"))


@events.route("/events/signup/<int:event_id>", methods=["POST"])
@login_required
def signup_event(event_id):
    """Register user for an event with enhanced security and validation"""
    user_id = current_user.id
    if not user_id:
        logging.warning("Something is wrong, no user ID found for this user.")
        log_security_event('Event signup attempted without valid user ID', success=False)
        flash("Unexpected error occurred", "danger")
        return redirect(url_for("dashboard"))

    try:
        # Validate event_id is a positive integer
        if event_id <= 0:
            log_security_event(f'Invalid event ID provided for signup: {event_id}', success=False)
            flash("Invalid event ID", "danger")
            return redirect(url_for("events.list_events"))

        user = db.session.query(User).get(user_id)
        event = db.session.query(Event).get(event_id)

        if not user or not event:
            logging.warning(f"Attempt to access invalid user or event")
            log_security_event(f'Event signup failed - invalid user ({user_id}) or event ({event_id})', success=False)
            flash("Invalid user or event", "danger")
            return redirect(url_for("events.list_events"))

        if event in user.events:
            log_security_event(f'User {user.username} attempted duplicate registration for event {event_id}',
                               success=False)
            flash("Cannot register for the same event multiple times", "danger")
            return redirect(url_for("events.list_events"))
        else:
            event_title = sanitize_input(event.title) if event.title else f"Event {event_id}"
            user.events.append(event)
            db.session.commit()

            log_security_event(f'User {user.username} registered for event: {event_title}', success=True)
            flash(f"You have successfully signed up for event ({event_title})", "success")

    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when trying to register for an event: {e}")
        log_security_event(
            f'Event signup failed for user {current_user.username if current_user.is_authenticated else "unknown"}',
            success=False, details=str(e))
        flash("An error occurred when registering", "danger")

    return redirect(url_for("events.list_events"))


@events.route("/events/profile", methods=["GET"])
@login_required
def profile_events():
    """Display user's registered events with sanitized data"""
    user_id = current_user.id
    if not user_id:
        logging.warning("Something is wrong, no user ID found for this user.")
        log_security_event('Profile events accessed without valid user ID', success=False)
        flash("Unexpected error occurred", "danger")
        return redirect(url_for("dashboard"))

    try:
        user = db.session.query(User).get(user_id)
        if not user:
            logging.warning("No/invalid user ID provided when querying user event history")
            log_security_event(f'Profile events failed - user not found: {user_id}', success=False)
            flash("Please log in before attempting to retrieve event history", "danger")
            return redirect(url_for("auth.user_login"))

        signed_events = user.events
        events = []

        # Sanitize event data before sending to template
        for event in signed_events:
            event_dict = event.to_dict()
            # Sanitize text fields in the event dictionary
            if 'title' in event_dict and event_dict['title']:
                event_dict['title'] = sanitize_input(event_dict['title'])
            if 'description' in event_dict and event_dict['description']:
                event_dict['description'] = sanitize_input(event_dict['description'])
            events.append(event_dict)

        log_security_event(f'User {user.username} viewed their event profile', success=True)

    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when trying to retrieve user event history: {e}")
        log_security_event(
            f'Profile events failed for user {current_user.username if current_user.is_authenticated else "unknown"}',
            success=False, details=str(e))
        flash("An error occurred when attempting to load your event history", "danger")
        events = []

    return render_template("profile_events.html", events=events)


# Additional helper function for event data validation
def validate_event_data(title, description):
    """
    Validate and sanitize event data
    Returns: (is_valid, sanitized_data, errors)
    """
    errors = []
    sanitized_data = {}

    # Validate and sanitize title
    if not title or not title.strip():
        errors.append("Event title is required")
    else:
        sanitized_title = sanitize_input(title.strip())
        if len(sanitized_title) > 200:  # Assuming max title length
            errors.append("Event title is too long (maximum 200 characters)")
        else:
            sanitized_data['title'] = sanitized_title

    # Validate and sanitize description
    if description:
        sanitized_description = sanitize_input(description.strip())
        if len(sanitized_description) > 2000:  # Assuming max description length
            errors.append("Event description is too long (maximum 2000 characters)")
        else:
            sanitized_data['description'] = sanitized_description
    else:
        sanitized_data['description'] = ""

    return (len(errors) == 0, sanitized_data, errors)


# Rate limiting decorator for event operations
def event_rate_limit(max_requests=10, window_seconds=60):
    """
    Rate limiting specifically for event operations
    """

    def decorator(f):
        # Simple in-memory storage (use Redis in production)
        request_counts = {}

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return f(*args, **kwargs)

            identifier = f"{current_user.id}_{request.endpoint}"
            now = datetime.utcnow()

            # Clean old entries
            request_counts[identifier] = [
                timestamp for timestamp in request_counts.get(identifier, [])
                if timestamp > now - timedelta(seconds=window_seconds)
            ]

            # Check rate limit
            if len(request_counts.get(identifier, [])) >= max_requests:
                log_security_event(f"Event operation rate limit exceeded for user {current_user.username}",
                                   success=False)
                flash("Too many requests. Please wait before trying again.", "warning")
                return redirect(url_for('events.list_events'))

            # Add current request
            request_counts.setdefault(identifier, []).append(now)

            return f(*args, **kwargs)

        return decorated_function

    return decorator