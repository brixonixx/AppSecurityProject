"""
Script to check all users in the database
"""
from flask import Flask
from models import db, User
from config import Config
from datetime import datetime

# Create app context
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def list_all_users():
    with app.app_context():
        print("\n📋 All Users in Database")
        print("="*80)
        
        users = User.query.all()
        
        if not users:
            print("❌ No users found in the database!")
            return
        
        print(f"Total users: {len(users)}")
        print("-"*80)
        
        # Header
        print(f"{'ID':<5} {'Username':<15} {'Email':<30} {'Admin':<7} {'Active':<8} {'Locked':<7}")
        print("-"*80)
        
        for user in users:
            # Check if account is locked
            locked = "Yes" if user.failed_login_attempts >= 5 else "No"
            if user.account_locked_until and user.account_locked_until > datetime.utcnow():
                locked = "LOCKED"
            
            print(f"{user.id:<5} {user.username:<15} {user.email:<30} "
                  f"{'Yes' if user.is_admin else 'No':<7} "
                  f"{'Yes' if user.is_active else 'No':<8} "
                  f"{locked:<7}")
        
        print("-"*80)
        
        # Show admin users specifically
        admin_users = [u for u in users if u.is_admin]
        print(f"\n🔑 Admin users: {len(admin_users)}")
        for admin in admin_users:
            print(f"  - {admin.username} ({admin.email})")
        
        # Show locked users
        locked_users = [u for u in users if u.failed_login_attempts >= 5]
        if locked_users:
            print(f"\n🔒 Locked users: {len(locked_users)}")
            for user in locked_users:
                print(f"  - {user.username} ({user.email}) - {user.failed_login_attempts} failed attempts")

if __name__ == '__main__':
    list_all_users()