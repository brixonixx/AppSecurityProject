# Create a new file: email_service.py

"""
Universal Email Service for SilverSage
Sends emails to ALL users regardless of registration method
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import make_msgid
from flask import current_app
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Universal email service using SMTP"""
    
    @staticmethod
    def send_email(to_email, subject, body_text, body_html=None):
        """
        Send email using SMTP - works for ALL users
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            body_text (str): Plain text body
            body_html (str, optional): HTML body
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get email configuration
            smtp_server = current_app.config.get('MAIL_SERVER')
            smtp_port = current_app.config.get('MAIL_PORT', 587)
            smtp_username = current_app.config.get('MAIL_USERNAME')
            smtp_password = current_app.config.get('MAIL_PASSWORD')
            sender_email = current_app.config.get('MAIL_DEFAULT_SENDER')
            
            if not all([smtp_server, smtp_username, smtp_password, sender_email]):
                logger.error("Email configuration incomplete")
                return False
            
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"SilverSage <{sender_email}>"
            message['To'] = to_email
            message['Message-ID'] = make_msgid()
            message['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            # Attach text body
            text_part = MIMEText(body_text, 'plain')
            message.attach(text_part)
            
            # Attach HTML body if provided
            if body_html:
                html_part = MIMEText(body_html, 'html')
                message.attach(html_part)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # Enable encryption
                server.login(smtp_username, smtp_password)
                
                # Send email
                text = message.as_string()
                server.sendmail(sender_email, to_email, text)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed - check email credentials")
            return False
        except smtplib.SMTPRecipientsRefused:
            logger.error(f"Recipient email address refused: {to_email}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(user, reset_url):
        """
        Send password reset email to ANY user
        
        Args:
            user: User object
            reset_url (str): Password reset URL
            
        Returns:
            bool: True if email sent successfully
        """
        subject = "SilverSage - Password Reset Request"
        
        # Plain text version
        body_text = f"""
Hello {user.first_name or user.username},

You requested a password reset for your SilverSage account.

To reset your password, click on the following link:
{reset_url}

This link will expire in 1 hour for security reasons.

If you didn't request this password reset, please ignore this email or contact our support team if you have concerns.

Best regards,
The SilverSage Team

---
SilverSage - Supporting our senior community
If you have any questions, contact us at support@silversage.com
        """.strip()
        
        # HTML version (optional - prettier formatting)
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Password Reset - SilverSage</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2c5282; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
        .button {{ display: inline-block; background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 14px; color: #666; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{user.first_name or user.username}</strong>,</p>
            
            <p>You requested a password reset for your SilverSage account.</p>
            
            <p>Click the button below to reset your password:</p>
            
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset My Password</a>
            </p>
            
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 4px;">
                {reset_url}
            </p>
            
            <div class="warning">
                <strong>⚠️ Important:</strong> This link will expire in 1 hour for security reasons.
            </div>
            
            <p>If you didn't request this password reset, please ignore this email or contact our support team if you have concerns.</p>
            
            <p>Best regards,<br>
            <strong>The SilverSage Team</strong></p>
        </div>
        <div class="footer">
            <p><strong>SilverSage</strong> - Supporting our senior community</p>
            <p>If you have any questions, contact us at support@silversage.com</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return EmailService.send_email(user.email, subject, body_text, body_html)
    
    @staticmethod
    def send_2fa_code_email(user, code):
        """
        Send 2FA code email to ANY user
        
        Args:
            user: User object
            code (str): 6-digit verification code
            
        Returns:
            bool: True if email sent successfully
        """
        subject = "SilverSage - Your Security Code"
        
        body_text = f"""
Hello {user.first_name or user.username},

Your SilverSage security code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, please contact support immediately.

Best regards,
The SilverSage Team
        """.strip()
        
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Security Code - SilverSage</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2c5282; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; text-align: center; }}
        .code {{ font-size: 32px; font-weight: bold; background: white; padding: 20px; margin: 20px 0; border-radius: 8px; letter-spacing: 8px; border: 2px solid #28a745; color: #28a745; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 14px; color: #666; }}
        .warning {{ background: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Your Security Code</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{user.first_name or user.username}</strong>,</p>
            
            <p>Your SilverSage security code is:</p>
            
            <div class="code">{code}</div>
            
            <p><strong>⏰ This code expires in 10 minutes</strong></p>
            
            <div class="warning">
                <strong>⚠️ Security Alert:</strong> If you didn't request this code, please contact support immediately.
            </div>
            
            <p>Best regards,<br>
            <strong>The SilverSage Team</strong></p>
        </div>
        <div class="footer">
            <p>If you have any questions, contact us at support@silversage.com</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return EmailService.send_email(user.email, subject, body_text, body_html)
    
    @staticmethod
    def test_email_configuration():
        """
        Test email configuration
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            smtp_server = current_app.config.get('MAIL_SERVER')
            smtp_port = current_app.config.get('MAIL_PORT', 587)
            smtp_username = current_app.config.get('MAIL_USERNAME')
            smtp_password = current_app.config.get('MAIL_PASSWORD')
            
            if not all([smtp_server, smtp_username, smtp_password]):
                return False, "Email configuration incomplete"
            
            # Test SMTP connection
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
            
            return True, "Email configuration is working correctly"
            
        except smtplib.SMTPAuthenticationError:
            return False, "SMTP authentication failed - check email credentials"
        except Exception as e:
            return False, f"Email configuration error: {str(e)}"
        
    @staticmethod
    def generate_test_backup_codes():
        """Generate test backup codes for development/testing"""
        import secrets
        
        # Generate 10 backup codes
        backup_codes = []
        for i in range(10):
            code = f"{secrets.randbelow(100000000):08d}"
            backup_codes.append(code)
        
        return backup_codes
    
    @staticmethod
    def create_test_user_with_2fa(username="testuser", email="test@example.com"):
        """Create a test user with 2FA enabled for testing backup codes"""
        from models import User, TwoFactorAuth, db
        import secrets
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return existing_user, existing_user.two_factor_auth
        
        # Create test user
        user = User(
            username=username,
            email=email,
            first_name="Test",
            last_name="User",
            is_active=True
        )
        user.set_password("TestPassword123!")
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Create 2FA setup
        backup_codes = EmailService.generate_test_backup_codes()
        
        two_fa = TwoFactorAuth(
            user_id=user.id,
            is_enabled=True,
            backup_codes=','.join(backup_codes)
        )
        
        db.session.add(two_fa)
        db.session.commit()
        
        print(f"Test user created: {email}")
        print(f"Password: TestPassword123!")
        print(f"Backup codes: {backup_codes}")
        
        return user, two_fa