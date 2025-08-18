# Updated forms.py - Fixed TwoFactorForm to properly handle backup codes
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, IntegerField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional, NumberRange
import re

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class TwoFactorForm(FlaskForm):
    """Form for 2FA verification during login - Fixed to properly handle backup codes"""
    code = StringField('Verification Code', validators=[
        Optional(),  # Changed from DataRequired to Optional
        Length(min=6, max=8, message='Invalid code length')
    ])
    backup_code = StringField('Or use backup code', validators=[
        Optional(),
        Length(min=8, max=8, message='Backup codes are 8 digits')
    ])
    submit = SubmitField('Verify')
    
    def validate(self, extra_validators=None):
        """Custom validation to ensure either code or backup_code is provided"""
        # First run the standard validation
        rv = FlaskForm.validate(self, extra_validators)
        
        # Check if at least one of the fields has data
        code_provided = self.code.data and self.code.data.strip()
        backup_code_provided = self.backup_code.data and self.backup_code.data.strip()
        
        if not code_provided and not backup_code_provided:
            # Add error to both fields
            self.code.errors.append('Please enter either a verification code or a backup code')
            self.backup_code.errors.append('Please enter either a verification code or a backup code')
            rv = False
        
        # Additional validation for each field if provided
        if code_provided:
            # Validate code format (should be 6 digits)
            if not re.match(r'^\d{6}$', self.code.data.strip()):
                self.code.errors.append('Verification code must be 6 digits')
                rv = False
        
        if backup_code_provided:
            # Validate backup code format (should be 8 digits)
            if not re.match(r'^\d{8}$', self.backup_code.data.strip()):
                self.backup_code.errors.append('Backup code must be 8 digits')
                rv = False
        
        return rv

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=20, message='Username must be between 3 and 20 characters')
    ])
    email = StringField('Email', validators=[
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
    submit = SubmitField('Register')
    
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

class ProfileForm(FlaskForm):
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
    profile_picture = FileField('Profile Picture', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Update Profile')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required'),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password'),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')

class ForgotPasswordForm(FlaskForm):
    """Form for requesting password reset"""
    email = StringField('Email Address', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    """Form for resetting password with token"""
    password = PasswordField('New Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')
    
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

class Enable2FAForm(FlaskForm):
    """Form for enabling 2FA"""
    confirm = BooleanField('I understand that I need access to my email to use 2FA', validators=[
        DataRequired(message='You must confirm you understand the requirement')
    ])
    submit = SubmitField('Enable Two-Factor Authentication')

class Verify2FASetupForm(FlaskForm):
    """Form for verifying 2FA setup"""
    code = StringField('Verification Code', validators=[
        DataRequired(message='Please enter the 6-digit code from your email'),
        Length(min=6, max=6, message='Code must be 6 digits')
    ])
    submit = SubmitField('Verify and Enable 2FA')

class Disable2FAForm(FlaskForm):
    """Form for disabling 2FA"""
    password = PasswordField('Current Password', validators=[
        DataRequired(message='Password is required to disable 2FA')
    ])
    confirm = BooleanField('I understand that disabling 2FA reduces my account security', validators=[
        DataRequired(message='You must confirm you understand the security implications')
    ])
    submit = SubmitField('Disable Two-Factor Authentication')

class EventForm(FlaskForm):
    title = StringField(
        "Event Title",
        validators=[
            DataRequired(message="Title is required"),
            Length(min=3, max=100, message="Title must be between 3 and 100 characters."),
        ],
    )
    description = StringField(
        "Description",
        validators=[
            DataRequired(message="Description is required"),
            Length(min=10, max=1000, message="Description must be between 10 and 1000 characters."),
        ],
    )
    image_file = FileField(
        "Event Image",
        validators=[FileAllowed(['jpg', 'jpeg', 'png'], "Only JPG, JPEG, and PNG files are allowed!")],
    )
    submit = SubmitField("Add Event")