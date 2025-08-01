"""
Database migration script to handle schema differences
"""
import pymysql
from config import Config
from urllib.parse import unquote
import sys

# Get database config
config = Config()

# Parse the connection details
import re
match = re.search(r'mysql\+pymysql://(.+):(.+)@(.+)/(.+)', config.SQLALCHEMY_DATABASE_URI)
if match:
    user = match.group(1)
    password = unquote(match.group(2))
    host = match.group(3)
    database = match.group(4)

print("🔧 Database Migration Tool")
print("="*50)
print(f"Host: {host}")
print(f"Database: {database}")
print(f"User: {user}")
print("="*50)

print("\nChoose an option:")
print("1. Create a new database 'elderly_app' for this application (SAFEST)")
print("2. Add missing columns to existing 'users' table")
print("3. Drop and recreate all tables (WARNING: Data loss!)")
print("4. Exit without changes")

choice = input("\nEnter your choice (1-4): ")

try:
    # Connect to MySQL
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with connection.cursor() as cursor:
        if choice == '1':
            # Create new database
            print("\n📦 Creating new database 'elderly_app'...")
            
            # First, connect without specifying database
            conn_no_db = pymysql.connect(
                host=host,
                user=user,
                password=password
            )
            
            with conn_no_db.cursor() as cursor_no_db:
                cursor_no_db.execute("CREATE DATABASE IF NOT EXISTS elderly_app")
                cursor_no_db.execute(f"GRANT ALL PRIVILEGES ON elderly_app.* TO '{user}'@'%'")
                cursor_no_db.execute("FLUSH PRIVILEGES")
            
            conn_no_db.close()
            
            print("✅ Database 'elderly_app' created successfully!")
            print("\n📝 Update your .env file:")
            print("MYSQL_DATABASE=elderly_app")
            print("\nThen restart your Flask application.")
            
        elif choice == '2':
            # Add missing columns
            print("\n🔨 Adding missing columns to existing users table...")
            
            # Get existing columns
            cursor.execute("DESCRIBE users")
            existing_columns = [col['Field'] for col in cursor.fetchall()]
            
            # Define required columns with their SQL definitions
            required_columns = {
                'password_hash': 'VARCHAR(256)',
                'first_name': 'VARCHAR(50)',
                'last_name': 'VARCHAR(50)',
                'age': 'INT',
                'contact_number': 'VARCHAR(20)',
                'profile_picture': 'VARCHAR(200) DEFAULT "default.png"',
                'is_admin': 'BOOLEAN DEFAULT FALSE',
                'is_active': 'BOOLEAN DEFAULT TRUE',
                'failed_login_attempts': 'INT DEFAULT 0',
                'last_failed_login': 'DATETIME',
                'account_locked_until': 'DATETIME',
                'password_reset_token': 'VARCHAR(100)',
                'password_reset_expiry': 'DATETIME',
                'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
                'last_login': 'DATETIME'
            }
            
            # Check if there's a password column to migrate
            cursor.execute("SHOW COLUMNS FROM users LIKE '%pass%'")
            password_cols = cursor.fetchall()
            old_password_col = None
            if password_cols:
                old_password_col = password_cols[0]['Field']
                print(f"Found existing password column: {old_password_col}")
            
            # Add missing columns
            for col_name, col_def in required_columns.items():
                if col_name not in existing_columns:
                    try:
                        print(f"Adding column: {col_name}")
                        cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                    except Exception as e:
                        print(f"⚠️  Could not add {col_name}: {str(e)}")
            
            # If there's an old password column, offer to migrate
            if old_password_col and old_password_col != 'password_hash':
                migrate_passwords = input(f"\nMigrate passwords from '{old_password_col}' to 'password_hash'? (y/n): ")
                if migrate_passwords.lower() == 'y':
                    cursor.execute(f"UPDATE users SET password_hash = {old_password_col} WHERE password_hash IS NULL")
                    print("✅ Passwords migrated")
            
            # Create other required tables
            print("\n📋 Creating additional tables...")
            
            # Password history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    password_hash VARCHAR(256),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    action VARCHAR(100) NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent VARCHAR(200),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    details TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            
            connection.commit()
            print("✅ Schema migration completed!")
            
        elif choice == '3':
            # Drop and recreate
            confirm = input("\n⚠️  WARNING: This will DELETE ALL DATA! Type 'DELETE' to confirm: ")
            if confirm == 'DELETE':
                print("\n🗑️  Dropping existing tables...")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                cursor.execute("DROP TABLE IF EXISTS audit_logs")
                cursor.execute("DROP TABLE IF EXISTS password_history")
                cursor.execute("DROP TABLE IF EXISTS users")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                connection.commit()
                print("✅ Tables dropped. Restart Flask app to create new tables.")
            else:
                print("❌ Operation cancelled.")
                
        else:
            print("\n👋 Exiting without changes.")
            
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
finally:
    if 'connection' in locals():
        connection.close()

print("\n✅ Migration script completed!")