"""
Updated admin_forms.py with volunteer options
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, IntegerField, BooleanField, EmailField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional, NumberRange
import re

class AdminUserCreationForm(FlaskForm):
    """Form for admin to create new users"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=20, message='Username must be between 3 and 20 characters')
    ])
    email = EmailField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    is_admin = BooleanField('Grant Administrator Privileges')
    is_volunteer = BooleanField('Grant Volunteer Status')
    approve_volunteer = BooleanField('Approve Volunteer Immediately')
    submit = SubmitField('Create User')
    
    def validate_password(self, field):
        """Custom password validation for security"""
        password = field.data
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', password):
            raise ValidationError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError('Password must contain at least one special character')

class AdminEditUserForm(FlaskForm):
    """Form for admin to edit existing users"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=20, message='Username must be between 3 and 20 characters')
    ])
    email = EmailField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email address')
    ])
    first_name = StringField('First Name', validators=[
        Optional(),
        Length(max=50)
    ])
    last_name = StringField('Last Name', validators=[
        Optional(),
        Length(max=50)
    ])
    age = IntegerField('Age', validators=[
        Optional(),
        NumberRange(min=1, max=150, message='Please enter a valid age')
    ])
    contact_number = StringField('Contact Number', validators=[
        Optional(),
        Length(max=20)
    ])
    is_admin = BooleanField('Administrator Privileges')
    is_active = BooleanField('Account Active')
    is_volunteer = BooleanField('Volunteer Status')
    volunteer_approved = BooleanField('Volunteer Approved')
    submit = SubmitField('Save Changes')

class VolunteerEditForm(FlaskForm):
    """Form for admin to edit volunteer-specific information"""
    volunteer_bio = TextAreaField('Volunteer Bio', validators=[
        Optional(),
        Length(max=1000, message='Bio must be less than 1000 characters')
    ])
    volunteer_skills = TextAreaField('Skills & Expertise', validators=[
        Optional(),
        Length(max=500, message='Skills must be less than 500 characters')
    ])
    volunteer_availability = StringField('Availability', validators=[
        Optional(),
        Length(max=200, message='Availability must be less than 200 characters')
    ])
    volunteer_approved = BooleanField('Approve Volunteer')
    submit = SubmitField('Update Volunteer Info')

# Form for your teammate to use for volunteer applications
class VolunteerApplicationForm(FlaskForm):
    """Form for users to apply as volunteers"""
    volunteer_bio = TextAreaField('Why do you want to volunteer?', validators=[
        DataRequired(message='Please tell us why you want to volunteer'),
        Length(min=50, max=1000, message='Please provide at least 50 characters')
    ], description='Tell us about your motivation and what you hope to contribute')
    
    volunteer_skills = TextAreaField('Skills & Experience', validators=[
        Optional(),
        Length(max=500, message='Skills must be less than 500 characters')
    ], description='What skills, experience, or expertise can you bring?')
    
    volunteer_availability = StringField('Availability', validators=[
        Optional(),
        Length(max=200, message='Availability must be less than 200 characters')
    ], description='When are you generally available? (e.g., "Weekdays 9-5", "Weekends", "Flexible")')
    
    agree_terms = BooleanField('I agree to the volunteer terms and conditions', validators=[
        DataRequired(message='You must agree to the terms and conditions')
    ])
    
    submit = SubmitField('Submit Volunteer Application')