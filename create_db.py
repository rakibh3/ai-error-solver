import psycopg2
from urllib.parse import urlparse
from app.core.config import DATABASE_URL

conn = None
cursor = None

# Parse DATABASE_URL
url = urlparse(DATABASE_URL)

try:
    conn = psycopg2.connect(
       dbname= url.path[1:],
       user=url.username,
       password=url.password,
       host=url.hostname,
       port=url.port
    )
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    print("Database connection successful")
except Exception as e:
    print(f"Database connection failed: {e}")
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
    print("Database connection closed")
