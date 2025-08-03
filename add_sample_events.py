#!/usr/bin/env python3
"""
Add sample events to the database for testing
"""

from main import create_app
from models import db, Event, User
from datetime import datetime

def add_sample_events():
    """Add some sample events for testing"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get an admin user to create events
            admin_user = User.query.filter_by(is_admin=True).first()
            if not admin_user:
                print("❌ No admin user found. Please create an admin user first.")
                return False
            
            print(f"👤 Using admin user: {admin_user.username}")
            
            # Sample events data
            sample_events = [
                {
                    "title": "Morning Tai Chi Class",
                    "description": "Join us for a relaxing morning Tai Chi session in the park. Perfect for seniors looking to improve balance and flexibility. All skill levels welcome!",
                    "image_file": None
                },
                {
                    "title": "Technology Workshop",
                    "description": "Learn how to use smartphones and tablets safely. We'll cover basic apps, video calling with family, and online safety tips.",
                    "image_file": None
                },
                {
                    "title": "Community Garden Project",
                    "description": "Help us plant and maintain our community garden. Great way to stay active, meet neighbors, and grow fresh vegetables together.",
                    "image_file": None
                },
                {
                    "title": "Arts & Crafts Circle",
                    "description": "Weekly arts and crafts session where we create beautiful projects together. This week we're making holiday decorations!",
                    "image_file": None
                },
                {
                    "title": "Health & Wellness Seminar",
                    "description": "Join our local health expert for tips on staying healthy and active as we age. Includes Q&A session and light refreshments.",
                    "image_file": None
                }
            ]
            
            events_created = 0
            
            for event_data in sample_events:
                # Check if event already exists
                existing_event = Event.query.filter_by(title=event_data["title"]).first()
                if existing_event:
                    print(f"ℹ️ Event '{event_data['title']}' already exists")
                    continue
                
                # Create new event
                new_event = Event(
                    title=event_data["title"],
                    description=event_data["description"],
                    user_id=admin_user.id,
                    image_file=event_data["image_file"]
                )
                
                db.session.add(new_event)
                events_created += 1
                print(f"✅ Created event: {event_data['title']}")
            
            # Commit all changes
            db.session.commit()
            
            print(f"\n🎉 Successfully created {events_created} new events!")
            
            # Show all events
            all_events = Event.query.all()
            print(f"\n📋 Total events in database: {len(all_events)}")
            for event in all_events:
                print(f"  • ID {event.event_id}: {event.title}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating sample events: {str(e)}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("🎪 Adding Sample Events to SilverSage")
    print("=" * 50)
    
    success = add_sample_events()
    
    if success:
        print("\n✅ Sample events added successfully!")
        print("Visit https://localhost:5000/events/ to see the events")
        print("Visit https://localhost:5000/admin/events to manage events (admin only)")
    else:
        print("\n❌ Failed to add sample events. Please check the errors above.")