"""
Flask application factory for AuraMail.
Creates and configures Flask app instance without circular dependencies.
This module can be imported by both server.py and worker.py.
"""
import os
import sys
from flask import Flask
from flask_caching import Cache
from flask_cors import CORS
from flask_talisman import Talisman

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import configuration
from config import (
    FLASK_SECRET_KEY,
    DEBUG,
    CORS_ORIGINS,
    ALLOW_ALL_CORS,
    FORCE_HTTPS,
    CACHE_REDIS_URL,
    CACHE_DEFAULT_TIMEOUT
)

# Import database initialization
from database import db, init_db

# Import monitoring and logging
from utils.logging_config import setup_structured_logging, get_logger


def create_app():
    """
    Factory function to create and configure Flask application.
    This is the single source of truth for Flask app creation.
    
    Returns:
        Flask application instance with all extensions initialized
    """
    # Initialize Flask application
    app = Flask(__name__)
    app.secret_key = FLASK_SECRET_KEY
    
    # Session configuration - critical for OAuth callback to work
    # Make session permanent so it persists across requests
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours in seconds
    
    # Cookie configuration
    # CRITICAL: For development with self-signed cert, we MUST disable Secure flag
    # Otherwise browsers will reject cookies even on HTTPS
    if DEBUG:
        # Development: Allow cookies on localhost with self-signed cert
        app.config['SESSION_COOKIE_SECURE'] = False
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow cookies on redirect from OAuth
        app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cookies on localhost
    else:
        # Production: Use secure cookies on real HTTPS
        app.config['SESSION_COOKIE_SECURE'] = FORCE_HTTPS
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['SESSION_COOKIE_DOMAIN'] = None
    
    app.config['DEBUG'] = DEBUG
    
    # Check for TESTING mode from environment or config
    # This allows tests to set TESTING before app creation
    import os
    is_testing = os.getenv('TESTING', 'False').lower() in ('true', '1', 'yes')
    if not is_testing:
        is_testing = app.config.get('TESTING', False)
    app.config['TESTING'] = is_testing
    
    # Initialize structured logging
    setup_structured_logging()
    get_logger(__name__)
    
    # Initialize database with connection pooling
    init_db(app)
    
    # Ensure database tables exist (create if they don't)
    # This is safe - db.create_all() only creates missing tables
    # This runs at app startup to ensure database is ready
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:
        # Log error but don't fail app startup
        # Tables will be created on first request or via init_database.py
        import warnings
        warnings.warn(f"Could not create database tables at startup: {e}. "
                     f"Run 'python init_database.py' to initialize database.")
    
    # Initialize cache - will be configured based on TESTING mode
    # Default to Redis, but use NullCache for tests (standard Flask-Caching approach)
    cache = Cache()
    
    # Configure cache based on TESTING mode
    # When TESTING=True, NullCache simply ignores cache decorators (no caching)
    if app.config.get('TESTING', False):
        cache_config = {
            'CACHE_TYPE': 'NullCache',
            'CACHE_NO_NULL_WARNING': True  # Suppress warning about NullCache
        }
        app.config['CACHE_TYPE'] = 'NullCache'
    else:
        cache_config = {
            'CACHE_TYPE': 'RedisCache',
            'CACHE_REDIS_URL': CACHE_REDIS_URL,
            'CACHE_DEFAULT_TIMEOUT': CACHE_DEFAULT_TIMEOUT
        }
    
    cache.init_app(app, config=cache_config)
    
    # Store cache instance in app for access
    app.cache = cache
    
    # Import routes after app is created to avoid circular imports
    # Routes will be registered when server.py imports this app
    
    # Security: CORS Configuration
    if ALLOW_ALL_CORS:
        # WARNING: Only for development! Never use in production
        CORS(app)
        if not DEBUG:
            import warnings
            warnings.warn("ALLOW_ALL_CORS is True but DEBUG is False. This is unsafe for production!")
    else:
        # Production: Only allow specific origins
        if CORS_ORIGINS:
            CORS(app, resources={
                r"/api/*": {"origins": CORS_ORIGINS},
                r"/sort": {"origins": CORS_ORIGINS},
                r"/callback": {"origins": CORS_ORIGINS}
            })
    
    # Security: HTTP Headers Protection
    # For development: disable force_https to allow cookies on localhost with self-signed cert
    # For production: enable force_https for security
    talisman_force_https = FORCE_HTTPS if not DEBUG else False
    
    Talisman(app,
        force_https=talisman_force_https,
        content_security_policy={
            'default-src': ["'self'"],
            'script-src': ["'self'", 'https://apis.google.com', 'https://cdn.jsdelivr.net', "'unsafe-inline'", "'unsafe-hashes'"],
            'style-src': ["'self'", 'https://fonts.googleapis.com', "'unsafe-inline'"],
            'font-src': ["'self'", 'https://fonts.gstatic.com'],
            'img-src': ["'self'", 'data:', 'https:'],
            'connect-src': ["'self'", 'https://www.googleapis.com', 'https://*.googleapis.com', 'https://cdn.jsdelivr.net']
        },
        content_security_policy_nonce_in=[],
        frame_options='DENY',
        # Only enable HSTS in production (with real HTTPS)
        strict_transport_security=talisman_force_https,
        strict_transport_security_max_age=31536000 if talisman_force_https else 0,
        strict_transport_security_include_subdomains=True if talisman_force_https else False
    )
    
    return app

