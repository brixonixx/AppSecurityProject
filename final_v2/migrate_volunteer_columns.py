# migrate_volunteer_columns.py
"""
Migration script to add volunteer-related columns to existing users table
Run this script to update your database schema
"""

from sqlalchemy import text, create_engine, inspect
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add volunteer columns to existing users table"""
    
    # Create engine
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    
    try:
        with engine.connect() as connection:
            # Start transaction
            trans = connection.begin()
            
            try:
                logger.info("Starting volunteer columns migration...")
                
                # Check if users table exists
                inspector = inspect(engine)
                if 'users' not in inspector.get_table_names():
                    logger.error("Users table does not exist. Please run the main application first.")
                    return False
                
                # Get existing columns
                existing_columns = [col['name'] for col in inspector.get_columns('users')]
                logger.info(f"Existing columns: {existing_columns}")
                
                # Add volunteer columns if they don't exist
                columns_to_add = [
                    ("is_volunteer", "BOOLEAN DEFAULT FALSE"),
                    ("volunteer_approved", "BOOLEAN DEFAULT FALSE"),
                    ("volunteer_approved_at", "DATETIME NULL"),
                    ("volunteer_approved_by", "INTEGER NULL"),
                    ("volunteer_bio", "TEXT NULL"),
                    ("volunteer_skills", "TEXT NULL"),
                    ("volunteer_availability", "VARCHAR(200) NULL"),
                    ("volunteer_applied_at", "DATETIME NULL")
                ]
                
                for column_name, column_def in columns_to_add:
                    if column_name not in existing_columns:
                        # MySQL syntax for adding columns
                        sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_def}"
                        logger.info(f"Adding column: {column_name}")
                        connection.execute(text(sql))
                    else:
                        logger.info(f"Column {column_name} already exists, skipping...")
                
                # Add foreign key constraint for volunteer_approved_by if it doesn't exist
                try:
                    if 'volunteer_approved_by' not in existing_columns:
                        logger.info("Adding foreign key constraint for volunteer_approved_by...")
                        fk_sql = """
                        ALTER TABLE users 
                        ADD CONSTRAINT fk_volunteer_approved_by 
                        FOREIGN KEY (volunteer_approved_by) REFERENCES users(id)
                        """
                        connection.execute(text(fk_sql))
                except Exception as e:
                    logger.warning(f"Could not add foreign key constraint: {e}")
                    # Continue anyway - foreign key is optional
                
                # Create volunteer events table if it doesn't exist
                if 'volunteer_events' not in inspector.get_table_names():
                    logger.info("Creating volunteer_events table...")
                    volunteer_events_sql = """
                    CREATE TABLE volunteer_events (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        event_date DATETIME NOT NULL,
                        location VARCHAR(200),
                        max_volunteers INTEGER DEFAULT 10,
                        created_by INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        FOREIGN KEY (created_by) REFERENCES users(id)
                    )
                    """
                    connection.execute(text(volunteer_events_sql))
                
                # Create volunteer registrations table if it doesn't exist
                if 'volunteer_registrations' not in inspector.get_table_names():
                    logger.info("Creating volunteer_registrations table...")
                    volunteer_registrations_sql = """
                    CREATE TABLE volunteer_registrations (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        user_id INTEGER NOT NULL,
                        event_id INTEGER NOT NULL,
                        registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(20) DEFAULT 'registered',
                        notes TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (event_id) REFERENCES volunteer_events(id),
                        UNIQUE KEY unique_registration (user_id, event_id)
                    )
                    """
                    connection.execute(text(volunteer_registrations_sql))
                
                # Commit transaction
                trans.commit()
                logger.info("✅ Migration completed successfully!")
                
                # Verify the changes
                updated_columns = [col['name'] for col in inspector.get_columns('users')]
                new_columns = set(updated_columns) - set(existing_columns)
                if new_columns:
                    logger.info(f"✅ New columns added: {new_columns}")
                else:
                    logger.info("ℹ️ No new columns were added (they already existed)")
                
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Migration failed: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful"""
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    
    try:
        with engine.connect() as connection:
            inspector = inspect(engine)
            
            # Check users table columns
            users_columns = [col['name'] for col in inspector.get_columns('users')]
            
            required_volunteer_columns = [
                'is_volunteer', 'volunteer_approved', 'volunteer_approved_at',
                'volunteer_approved_by', 'volunteer_bio', 'volunteer_skills',
                'volunteer_availability', 'volunteer_applied_at'
            ]
            
            missing_columns = []
            for col in required_volunteer_columns:
                if col not in users_columns:
                    missing_columns.append(col)
            
            if missing_columns:
                logger.error(f"❌ Migration verification failed. Missing columns: {missing_columns}")
                return False
            
            # Check if volunteer tables exist
            tables = inspector.get_table_names()
            required_tables = ['volunteer_events', 'volunteer_registrations']
            
            missing_tables = []
            for table in required_tables:
                if table not in tables:
                    missing_tables.append(table)
            
            if missing_tables:
                logger.warning(f"⚠️ Optional volunteer tables not created: {missing_tables}")
            
            logger.info("✅ Migration verification successful!")
            logger.info(f"📊 Users table now has {len(users_columns)} columns")
            logger.info(f"📊 Database has {len(tables)} tables")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("🔄 SilverSage Volunteer Columns Migration")
    print("="*60)
    
    print("\n1. Running migration...")
    if run_migration():
        print("\n2. Verifying migration...")
        if verify_migration():
            print("\n✅ Migration completed successfully!")
            print("\nYour database now supports volunteer functionality.")
            print("\nNext steps:")
            print("- Update your models.py with the new User model")
            print("- Your teammate can now create volunteer signup forms")
            print("- Admin panel can manage volunteer approvals")
        else:
            print("\n❌ Migration verification failed!")
    else:
        print("\n❌ Migration failed!")
    
    print("\n" + "="*60)