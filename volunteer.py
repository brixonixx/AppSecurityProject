# volunteer.py - Volunteer routes and functionality
from flask import render_template, request, redirect, url_for, flash, session, Blueprint, jsonify
from flask_login import login_required, current_user
from models import *
import logging
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


volunteer = Blueprint('volunteer', __name__)

### ------------------ HELPER FUNCTIONS ------------------- ###

def is_user_volunteer():
    """Check if current user is a volunteer"""
    # Force testuser to be a volunteer for testing
    if current_user.is_authenticated and current_user.username == 'testuser':
        return True
    
    # Check if user is authenticated and has is_volunteer field set to True
    if current_user.is_authenticated:
        # Direct access to current_user.is_volunteer field from database
        return getattr(current_user, 'is_volunteer', False)
    
    return False

def get_current_username():
    """Get current user's username, compatible with both session and current_user"""
    if current_user.is_authenticated:
        return current_user.username
    return session.get('username')

### ------------------ VOLUNTEER ROUTES ------------------- ###

@volunteer.route("/")
def volunteer_home():
    """Main volunteer page - redirects based on volunteer status"""
    if not current_user.is_authenticated:
        flash("Login required", "warning")
        return redirect(url_for('auth.login'))
    
    # Check if user is a volunteer
    if is_user_volunteer():
        return redirect(url_for('volunteer.volunteer_map'))
    else:
        return render_template('volunteer.html')

@volunteer.route("/request", methods=['GET', 'POST'])
@login_required
def volunteer_request():
    """Handle volunteer help requests"""
    if request.method == 'POST':
        try:
            lat = request.form.get('lat', type=float)
            lng = request.form.get('lng', type=float)
            title = request.form.get('title', 'Help Request')
            description = request.form.get('description', 'User requested help')
            username = get_current_username()

            if lat is None or lng is None:
                flash("Location required", "danger")
                return redirect(url_for('volunteer.volunteer_request'))

            vr = VolunteerRequest(
                title=title,
                description=description,
                requester=username,
                latitude=lat,
                longitude=lng
            )
            db.session.add(vr)
            db.session.commit()
            flash("Help request sent!", "success")
            
            # Redirect based on volunteer status
            if is_user_volunteer():
                return redirect(url_for('volunteer.volunteer_map'))
            else:
                return redirect(url_for('volunteer.volunteer_home'))
                
        except Exception as e:
            db.session.rollback()
            logging.exception(f"An exception occurred when creating volunteer request: {e}")
            flash("An error occurred when creating the request", "danger")

    return render_template('volunteer_request.html')

@volunteer.route("/map")
@login_required
def volunteer_map():
    """Volunteer map page - only for registered volunteers"""
    if not current_user.is_authenticated:
        flash("Login required", "warning")
        return redirect(url_for('auth.login'))

    # Check if user is a volunteer
    if not is_user_volunteer():
        flash("You must be a registered volunteer to view this page", "danger")
        return redirect(url_for('volunteer.volunteer_home'))

    try:
        requests = VolunteerRequest.query.all()
        return render_template('volunteer_map.html', requests=requests)
    except Exception as e:
        logging.exception(f"An exception occurred when loading volunteer map: {e}")
        flash("An error occurred when loading the map", "danger")
        return redirect(url_for('volunteer.volunteer_home'))

@volunteer.route("/register", methods=['GET', 'POST'])
@login_required
def register_volunteer():
    """Register as a volunteer"""
    if not current_user.is_authenticated:
        flash("Login required to register as a volunteer", "warning")
        return redirect(url_for('auth.login'))

    # Force testuser to be volunteer automatically
    if current_user.username == 'testuser':
        flash("Testuser is automatically a volunteer!", "info")
        return redirect(url_for('volunteer.volunteer_map'))

    user = User.query.filter_by(username=current_user.username).first()
    if not user:
        flash("User not found. Please log in again.", "danger")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        try:
            user.is_volunteer = True
            db.session.commit()
            flash("You are now registered as a volunteer!", "success")
            return redirect(url_for('volunteer.volunteer_map'))
        except Exception as e:
            db.session.rollback()
            logging.exception(f"An exception occurred when registering volunteer: {e}")
            flash("Error registering as volunteer. Please contact administrator.", "danger")
            return redirect(url_for('volunteer.volunteer_home'))

    return render_template('register_volunteer.html', user=user)

### ------------------ VOLUNTEER REQUEST MANAGEMENT ------------------- ###

@volunteer.route("/go/<int:request_id>", methods=['DELETE', 'POST'])
@login_required
def volunteer_go_to_request(request_id):
    """Accept and remove a volunteer request"""
    if not current_user.is_authenticated:
        return jsonify({"success": False, "error": "Login required"}), 403

    # Check if user is a volunteer
    if not is_user_volunteer():
        return jsonify({"success": False, "error": "Only volunteers can do this"}), 403

    try:
        vr = VolunteerRequest.query.get_or_404(request_id)
        db.session.delete(vr)
        db.session.commit()
        
        if request.method == 'DELETE':
            return jsonify({"success": True, "message": "Help request accepted and removed"})
        else:
            flash("Help request accepted and removed!", "success")
            return redirect(url_for('volunteer.volunteer_map'))
            
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when accepting request {request_id}: {e}")
        
        if request.method == 'DELETE':
            return jsonify({"success": False, "error": "An error occurred"}), 500
        else:
            flash("An error occurred when accepting the request", "danger")
            return redirect(url_for('volunteer.volunteer_map'))

@volunteer.route("/claim/<int:request_id>", methods=['POST'])
@login_required
def claim_volunteer_request(request_id):
    """Claim a volunteer request"""
    if not current_user.is_authenticated:
        return jsonify({"success": False, "error": "Login required"}), 403

    try:
        vr = VolunteerRequest.query.get_or_404(request_id)
        
        if not vr.claimed_by:
            vr.claimed_by = get_current_username()
            db.session.commit()
            return jsonify({"success": True, "message": "Request claimed successfully"})
        else:
            return jsonify({"success": False, "error": "Request already claimed"}), 400
            
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when claiming request {request_id}: {e}")
        return jsonify({"success": False, "error": "An error occurred"}), 500

@volunteer.route("/delete/<int:request_id>", methods=['POST'])
@login_required
def delete_volunteer_request(request_id):
    """Delete own volunteer request"""
    if not current_user.is_authenticated:
        return jsonify({"success": False, "error": "Login required"}), 403

    try:
        vr = VolunteerRequest.query.get_or_404(request_id)
        
        # Only allow the original requester to delete their own request
        if vr.requester != get_current_username():
            return jsonify({"success": False, "error": "Not authorized"}), 403

        db.session.delete(vr)
        db.session.commit()
        return jsonify({"success": True, "message": "Request deleted successfully"})
        
    except Exception as e:
        db.session.rollback()
        logging.exception(f"An exception occurred when deleting request {request_id}: {e}")
        return jsonify({"success": False, "error": "An error occurred"}), 500

### ------------------ API ENDPOINTS ------------------- ###

@volunteer.route("/requests_json")
def volunteer_requests_json():
    """JSON API for volunteer requests"""
    try:
        current_username = get_current_username()
        is_volunteer = is_user_volunteer()
        
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
                "is_owner": (r.requester == current_username),
                "can_go": is_volunteer,
                "requester": r.requester
            })
            
        return jsonify(result)
        
    except Exception as e:
        logging.exception(f"An exception occurred when fetching requests JSON: {e}")
        return jsonify({"error": "An error occurred when fetching requests"}), 500

### ------------------ LEGACY COMPATIBILITY ROUTES ------------------- ###

# For backward compatibility with existing templates/links
@volunteer.route("/new", methods=['GET', 'POST'])
@login_required
def new_volunteer_request():
    """Legacy route - redirects to register if not volunteer, otherwise to request"""
    if not is_user_volunteer():
        return redirect(url_for('volunteer.register_volunteer'))
    else:
        return redirect(url_for('volunteer.volunteer_request'))

# Additional helper route for navbar logic
@volunteer.route("/check_status")
@login_required
def check_volunteer_status():
    """API endpoint to check if user is volunteer (for navbar logic)"""
    return jsonify({
        "is_volunteer": is_user_volunteer(),
        "username": get_current_username()
    })