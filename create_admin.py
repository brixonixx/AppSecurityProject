"""
Script to create or reset admin user
"""
from flask import Flask
from models import db, User
from config import Config
import sys

# Create app context
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def create_or_reset_admin():
    with app.app_context():
        print("🔧 Admin User Management")
        print("="*50)
        
        # Check if admin exists
        admin = User.query.filter_by(email='admin@silversage.com').first()
        
        if admin:
            print("✅ Admin user already exists!")
            print(f"Username: {admin.username}")
            print(f"Email: {admin.email}")
            
            reset = input("\nDo you want to reset the admin password? (y/n): ")
            if reset.lower() == 'y':
                admin.set_password('Admin@123')
                # Reset any lockout
                admin.failed_login_attempts = 0
                admin.account_locked_until = None
                admin.is_active = True
                admin.is_admin = True
                db.session.commit()
                print("✅ Admin password reset to: Admin@123")
            else:
                print("No changes made.")
        else:
            # Create admin user
            print("❌ Admin user not found. Creating new admin...")
            
            admin = User(
                username='admin',
                email='admin@silversage.com',
                is_admin=True,
                is_active=True
            )
            admin.set_password('Admin@123')
            
            try:
                db.session.add(admin)
                db.session.commit()
                print("✅ Admin user created successfully!")
                print("Email: admin@silversage.com")
                print("Password: Admin@123")
            except Exception as e:
                print(f"❌ Error creating admin: {str(e)}")
                
                # Try with a different username if 'admin' is taken
                if "Duplicate entry" in str(e) and "username" in str(e):
                    print("\n🔄 Username 'admin' is taken. Trying 'administrator'...")
                    db.session.rollback()
                    
                    admin = User(
                        username='administrator',
                        email='admin@silversage.com',
                        is_admin=True,
                        is_active=True
                    )
                    admin.set_password('Admin@123')
                    
                    try:
                        db.session.add(admin)
                        db.session.commit()
                        print("✅ Admin user created with username: administrator")
                        print("Email: admin@silversage.com")
                        print("Password: Admin@123")
                    except Exception as e2:
                        print(f"❌ Error: {str(e2)}")
                        return
        
        # Show all admin users
        print("\n📋 All admin users in the system:")
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            status = "Active" if admin.is_active else "Inactive"
            locked = " (LOCKED)" if admin.failed_login_attempts >= 5 else ""
            print(f"  - {admin.username} ({admin.email}) - {status}{locked}")
        
        # Option to make any user an admin
        print("\n🔑 Make another user an admin?")
        username = input("Enter username to make admin (or press Enter to skip): ")
        if username:
            user = User.query.filter_by(username=username).first()
            if user:
                user.is_admin = True
                user.is_active = True
                db.session.commit()
                print(f"✅ {username} is now an admin!")
            else:
                print(f"❌ User '{username}' not found.")

if __name__ == '__main__':
    create_or_reset_admin()