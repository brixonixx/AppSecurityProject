#!/usr/bin/env python3
"""
simple_migration.py - Simple manual migration for Google OAuth columns

This script manually adds the required columns without complex SQLAlchemy imports
"""

import os
import sys
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get direct MySQL connection"""
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'ivp-silversage.duckdns.org'),
            user=os.getenv('MYSQL_USER', 'flask_user'),
            password=os.getenv('MYSQL_PASSWORD', 'Silvers@ge123'),
            database=os.getenv('MYSQL_DATABASE', 'flask_db'),
            charset='utf8mb4',
            port=3306,  # Add explicit port
            connect_timeout=10,  # Add timeout for remote connection
            read_timeout=10,
            write_timeout=10
        )
        return connection
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"   Host: {os.getenv('MYSQL_HOST', 'ivp-silversage.duckdns.org')}")
        print(f"   Database: {os.getenv('MYSQL_DATABASE', 'flask_db')}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Check if column exists"""
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = '{table_name}' 
        AND COLUMN_NAME = '{column_name}'
    """)
    return cursor.fetchone()[0] > 0

def check_table_exists(cursor, table_name):
    """Check if table exists"""
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = '{table_name}'
    """)
    return cursor.fetchone()[0] > 0

def add_google_oauth_columns(cursor):
    """Add Google OAuth columns to users table"""
    print("🔍 Adding Google OAuth columns...")
    
    columns_to_add = [
        ('google_id', 'VARCHAR(100) NULL UNIQUE'),
        ('google_access_token', 'TEXT NULL'),
        ('google_refresh_token', 'TEXT NULL'),
        ('email_verified', 'BOOLEAN DEFAULT FALSE')
    ]
    
    added_count = 0
    
    for column_name, column_definition in columns_to_add:
        if not check_column_exists(cursor, 'users', column_name):
            try:
                cursor.execute(f'ALTER TABLE users ADD COLUMN {column_name} {column_definition}')
                print(f"  ✅ Added column: {column_name}")
                added_count += 1
            except Exception as e:
                print(f"  ❌ Failed to add {column_name}: {e}")
        else:
            print(f"  ℹ️ Column {column_name} already exists")
    
    return added_count

def create_two_factor_table(cursor):
    """Create two_factor_auth table"""
    print("🔍 Creating two_factor_auth table...")
    
    if not check_table_exists(cursor, 'two_factor_auth'):
        try:
            cursor.execute('''
                CREATE TABLE two_factor_auth (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    is_enabled BOOLEAN DEFAULT FALSE,
                    backup_codes TEXT NULL,
                    temp_code VARCHAR(10) NULL,
                    temp_code_expires DATETIME NULL,
                    last_used DATETIME NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user_2fa (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            print("  ✅ Created two_factor_auth table")
            return True
        except Exception as e:
            print(f"  ❌ Failed to create two_factor_auth table: {e}")
            return False
    else:
        print("  ℹ️ two_factor_auth table already exists")
        return False

def main():
    print("="*60)
    print("🚀 Simple Google OAuth & 2FA Migration")
    print("="*60)
    
    # Get database connection
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Check if users table exists
        if not check_table_exists(cursor, 'users'):
            print("❌ Users table not found. Please run your main application first.")
            return False
        
        print("✅ Database connection successful")
        print("✅ Users table found")
        
        # Add Google OAuth columns
        google_columns_added = add_google_oauth_columns(cursor)
        
        # Create 2FA table
        tfa_table_created = create_two_factor_table(cursor)
        
        # Commit changes
        connection.commit()
        
        # Summary
        print("\n" + "="*40)
        print("Migration Summary")
        print("="*40)
        
        if google_columns_added > 0:
            print(f"✅ Added {google_columns_added} Google OAuth columns")
        else:
            print("ℹ️ Google OAuth columns already existed")
        
        if tfa_table_created:
            print("✅ Created two_factor_auth table")
        else:
            print("ℹ️ two_factor_auth table already existed")
        
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Add your Google Client ID and Secret to .env file")
        print("2. Start your application: python main.py")
        print("3. Test Google OAuth login")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)