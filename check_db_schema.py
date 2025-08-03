"""
Script to check the existing database schema and show differences
"""
import pymysql
from config import Config
from urllib.parse import unquote

# Get database config
config = Config()

# Parse the connection details
import re
match = re.search(r'mysql\+pymysql://(.+):(.+)@(.+)/(.+)', config.SQLALCHEMY_DATABASE_URI)
if match:
    user = match.group(1)
    password = unquote(match.group(2))  # Decode URL-encoded password
    host = match.group(3)
    database = match.group(4)
else:
    print("Could not parse database URI")
    exit(1)

print(f"Connecting to {host}/{database} as {user}...")

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
        # Get all tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("\n📊 Existing tables:")
        for table in tables:
            table_name = list(table.values())[0]
            print(f"  - {table_name}")
        
        # Check users table structure
        print("\n📋 Structure of 'users' table:")
        cursor.execute("DESCRIBE users")
        columns = cursor.fetchall()
        
        print("\nColumn Name | Type | Null | Key | Default | Extra")
        print("-" * 70)
        for col in columns:
            print(f"{col['Field']:20} | {col['Type']:20} | {col['Null']:4} | {col['Key']:3} | {col['Default'] or 'NULL':7} | {col['Extra']}")
        
        # Show sample data (without passwords)
        print("\n📝 Sample users (first 5):")
        cursor.execute("SELECT id, username, email, created_at FROM users LIMIT 5")
        users = cursor.fetchall()
        for user in users:
            print(f"  ID: {user['id']}, Username: {user['username']}, Email: {user['email']}, Created: {user['created_at']}")
            
        # Check what password column exists
        cursor.execute("SHOW COLUMNS FROM users LIKE '%pass%'")
        password_cols = cursor.fetchall()
        print(f"\n🔐 Password-related columns found: {[col['Field'] for col in password_cols]}")
        
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    print("\nMake sure your database is accessible and credentials are correct.")
finally:
    if 'connection' in locals():
        connection.close()

print("\n" + "="*70)
print("📌 SOLUTION OPTIONS:")
print("="*70)
print("1. Create a new database for this app (RECOMMENDED)")
print("2. Modify the existing table to match the app schema")
print("3. Update the app models to match the existing schema")
print("\nRun 'python migrate_db.py' to apply option 1 or 2")