import mysql.connector

def test_connection():
    try:
        # Establish a connection to the database
        connection = mysql.connector.connect(
            host='ivp-silversage.duckdns.org',
            port=3306,
            user='flask_user',
            password='Silvers@ge123',
            database='flask_db'
        )
        
        if connection.is_connected():
            print("Connection successful")
            cursor = connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("Available tables:", [tables[0] for tables in tables])
        
        connection.close()

    except Exception as e:
        print("Connection failed:", e)

if __name__ == "__main__":
    test_connection()       