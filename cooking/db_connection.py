import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Get a database connection using environment variables."""
    return psycopg2.connect(
        dbname=os.getenv('SUPABASE_DB_NAME'),
        user=os.getenv('SUPABASE_DB_USER'),
        password=os.getenv('SUPABASE_DB_PASSWORD'),
        host=os.getenv('SUPABASE_DB_HOST'),
        port=os.getenv('SUPABASE_DB_PORT')
    ) 