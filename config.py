"""
Configuration module for AuraMail.
Contains all environment variables and constants.
Uses python-decouple for secure secret management.
"""
import os
from decouple import config, Csv

# Google OAuth Configuration
CLIENT_SECRETS_FILE = config("GOOGLE_CLIENT_SECRETS_PATH", default="client_secret.json")
SCOPES = [
    # Gmail modify scope: allows read, modify, and delete emails
    # This is sufficient for email sorting operations including DELETE
    'https://www.googleapis.com/auth/gmail.modify',  # For email sorting, archiving, and deleting
    # Calendar scope: allows creating calendar events
    'https://www.googleapis.com/auth/calendar.events'  # For creating calendar events
]
# BASE_URI Configuration:
# - For local development: "https://127.0.0.1:5000" (default)
# - For production: Set BASE_URI environment variable to your production domain
# Example: BASE_URI=https://your-domain.com in .env file
BASE_URI = config("BASE_URI", default="https://127.0.0.1:5000")

# Flask Configuration
# CRITICAL: Generate a secure key using: python -c "import secrets; print(secrets.token_hex(32))"
FLASK_SECRET_KEY = config("FLASK_SECRET_KEY", default="VERY_SECRET_KEY_FOR_SESSIONS_CHANGE_IN_PRODUCTION")

# Gemini AI Configuration
def clean_api_key(api_key):
    """
    Cleans API key from extra spaces, quotes, and newlines.
    
    Args:
        api_key: Raw API key string from environment variable
    
    Returns:
        Cleaned API key string or None if empty
    """
    if not api_key:
        return None
    
    # Remove leading/trailing whitespace and quotes
    cleaned = api_key.strip().strip('"').strip("'").strip()
    
    # Remove newlines, carriage returns, and comments
    cleaned = cleaned.replace('\n', '').replace('\r', '')
    if '#' in cleaned:
        cleaned = cleaned.split('#')[0].strip()
    
    return cleaned if cleaned else None


# Get and clean GEMINI_API_KEY
_raw_gemini_key = config("GEMINI_API_KEY", default=None)
GEMINI_API_KEY = clean_api_key(_raw_gemini_key) if _raw_gemini_key else None

# Logging Configuration
LOG_FILE = config("LOG_FILE", default="auramail_log.json")
PROGRESS_FILE = config("PROGRESS_FILE", default="progress.json")

# Redis Configuration (for task queue)
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

# Redis Configuration for Caching (different database than RQ)
CACHE_REDIS_URL = config("CACHE_REDIS_URL", default="redis://localhost:6379/1")

# Cache Configuration
CACHE_DEFAULT_TIMEOUT = config("CACHE_DEFAULT_TIMEOUT", default=300, cast=int)  # 5 minutes default
CACHE_DASHBOARD_STATS_TIMEOUT = config("CACHE_DASHBOARD_STATS_TIMEOUT", default=300, cast=int)  # 5 minutes
CACHE_ACTION_HISTORY_TIMEOUT = config("CACHE_ACTION_HISTORY_TIMEOUT", default=60, cast=int)  # 1 minute

# Database Configuration
# Format: postgresql://user:password@host:port/dbname
# For SQLite (development): sqlite:///auramail.db
DATABASE_URL = config("DATABASE_URL", default="sqlite:///auramail.db")

# SQLAlchemy Connection Pool Settings
DB_POOL_SIZE = config("DB_POOL_SIZE", default=10, cast=int)
DB_MAX_OVERFLOW = config("DB_MAX_OVERFLOW", default=5, cast=int)
DB_POOL_RECYCLE = config("DB_POOL_RECYCLE", default=3600, cast=int)  # 1 hour

# Processing Configuration
MAX_MESSAGES_TO_PROCESS = config("MAX_MESSAGES_TO_PROCESS", default=50, cast=int)

# Calendar Integration Configuration
TIMEZONE = config("TIMEZONE", default="Europe/Kyiv")

# CORS Configuration
# Comma-separated list of allowed origins (e.g., "https://app.com,https://www.app.com")
CORS_ORIGINS = config("CORS_ORIGINS", default="", cast=Csv())
ALLOW_ALL_CORS = config("ALLOW_ALL_CORS", default=False, cast=bool)  # Only for development!

# Security Configuration
FORCE_HTTPS = config("FORCE_HTTPS", default=True, cast=bool)
DEBUG = config("DEBUG", default=False, cast=bool)

# Folders to process
FOLDERS_TO_PROCESS = ['INBOX', 'SPAM', 'TRASH']


def is_production_ready():
    """
    Checks if the application is configured for production.
    
    Returns:
        bool: True if all critical environment variables are set and not using defaults
    """
    # Check if critical variables are set and not using default values
    flask_secret = FLASK_SECRET_KEY
    gemini_key = GEMINI_API_KEY
    base_uri = BASE_URI
    debug_mode = DEBUG
    allow_all_cors = ALLOW_ALL_CORS
    
    # Production ready if:
    # 1. FLASK_SECRET_KEY is set and not default
    # 2. GEMINI_API_KEY is set
    # 3. BASE_URI is set and not localhost
    # 4. DEBUG is False
    # 5. CORS is not allowing all origins
    is_secure = (
        flask_secret and 
        flask_secret != "VERY_SECRET_KEY_FOR_SESSIONS_CHANGE_IN_PRODUCTION" and
        gemini_key is not None and
        base_uri and 
        "127.0.0.1" not in base_uri and 
        "localhost" not in base_uri.lower() and
        not debug_mode and
        not allow_all_cors
    )
    
    return is_secure

