#!/usr/bin/env python3
"""
Check if events table exists and create it if needed
Run this script to ensure your teammate's events functionality works
"""

from main import create_app
from models import db, Event, User
from sqlalchemy import text, inspect
import logging

def check_and_create_events_table():
    """Check if events table exists and create if needed"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get database inspector
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            print("🔍 Checking database tables...")
            print(f"📋 Existing tables: {existing_tables}")
            
            # Check if events table exists
            if 'events' in existing_tables:
                print("✅ Events table already exists!")
                
                # Check table structure
                print("\n📊 Events table structure:")
                columns = inspector.get_columns('events')
                for col in columns:
                    print(f"  • {col['name']}: {col['type']} {'(nullable)' if col['nullable'] else '(not null)'}")
                
                # Check if there are any events
                event_count = Event.query.count()
                print(f"\n📈 Current events count: {event_count}")
                
                if event_count > 0:
                    print("📋 Sample events:")
                    sample_events = Event.query.limit(3).all()
                    for event in sample_events:
                        print(f"  • ID {event.event_id}: {event.title}")
                
            else:
                print("❌ Events table does not exist. Creating it...")
                
                # Create just the events table
                Event.__table__.create(db.engine)
                print("✅ Events table created successfully!")
                
                # Verify creation
                if 'events' in inspector.get_table_names():
                    print("✅ Verification: Events table exists in database")
                else:
                    print("❌ Error: Events table creation failed")
                    return False
            
            # Check if user_event_association table exists (for many-to-many relationship)
            if 'user_event_association' in existing_tables:
                print("✅ User-Event association table exists")
            else:
                print("⚠️ User-Event association table missing. Creating it...")
                from models import user_event_association
                user_event_association.create(db.engine)
                print("✅ User-Event association table created")
            
            # Test creating a sample event (optional)
            print("\n🧪 Testing event creation...")
            
            # Get an admin user to create test event
            admin_user = User.query.filter_by(is_admin=True).first()
            if admin_user:
                # Check if test event already exists
                test_event = Event.query.filter_by(title="Sample Event").first()
                if not test_event:
                    test_event = Event(
                        title="Sample Event",
                        description="This is a test event created to verify the events system is working properly.",
                        user_id=admin_user.id,
                        image_file=None
                    )
                    db.session.add(test_event)
                    db.session.commit()
                    print(f"✅ Created test event with ID: {test_event.event_id}")
                else:
                    print(f"ℹ️ Test event already exists with ID: {test_event.event_id}")
            else:
                print("⚠️ No admin user found to create test event")
            
            print("\n🎉 Events system is ready!")
            print("📍 Your teammate can now:")
            print("  • Visit /admin/events to manage events (admin only)")
            print("  • Visit /events/ to view all events")
            print("  • Users can sign up for events")
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking/creating events table: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("🚀 SilverSage Events Table Setup")
    print("=" * 50)
    
    success = check_and_create_events_table()
    
    if success:
        print("\n✅ Setup completed successfully!")
        print("You can now run your main application with events support.")
    else:
        print("\n❌ Setup failed. Please check the errors above.")