import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    try:
        # Check that all required environment variables are set
        environment = os.getenv("FLASK_ENV", "local")

        # Set the database host based on the environment
        if environment == "local":
            db_host = "0.0.0.0"
        else:
            db_host = os.getenv("DB_HOST")

        db_name = os.getenv("DB_NAME")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_port = os.getenv("DB_PORT", "5432")  # PostgreSQL default port

        # Ensure no environment variable is missing
        if not all([db_host, db_name, db_user, db_password]):
            raise EnvironmentError("One or more required environment variables are missing.")

        # Establish the database connection using environment variables
        connection = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port
        )
        print("Database connection successful")
        return connection

    except psycopg2.DatabaseError as e:
        print(f"Database connection failed: {e}")
        raise
    except EnvironmentError as e:
        print(f"Environment variable error: {e}")
        raise
