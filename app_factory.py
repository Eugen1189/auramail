"""
Flask application factory for AuraMail.
Creates and configures Flask app instance with database and migrations.
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Import database
from database import db

# Initialize Flask-Caching
from flask_caching import Cache
cache = Cache()

# Initialize Flask-Migrate (optional - only if installed)
migrate = None
try:
    from flask_migrate import Migrate
    migrate = Migrate()
except ImportError:
    # Flask-Migrate not installed - migrations will use db.create_all() instead
    pass


def create_app():
    """
    Factory function to create and configure Flask application.
    
    Returns:
        Flask application instance with all extensions initialized
    """
    # Create Flask app
    app = Flask(__name__)
    
    # Import configuration
    from config import (
        FLASK_SECRET_KEY,
        DATABASE_URL,
        DEBUG,
        CACHE_REDIS_URL,
        CACHE_DEFAULT_TIMEOUT,
        CACHE_DASHBOARD_STATS_TIMEOUT,
        CACHE_ACTION_HISTORY_TIMEOUT
    )
    
    # Configure Flask app
    app.config['SECRET_KEY'] = FLASK_SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = DEBUG
    
    # Configure cache
    is_testing = os.getenv('TESTING', 'False').lower() in ('true', '1', 'yes')
    
    # Try to use Redis cache, fallback to NullCache if Redis is not available
    if is_testing:
        # Use NullCache for testing
        app.config['CACHE_TYPE'] = 'NullCache'
        app.config['CACHE_NO_NULL_WARNING'] = True
        print("✅ Cache: Using NullCache (testing mode)")
    else:
        # Try to connect to Redis, fallback to NullCache if unavailable
        try:
            import redis
            redis_client = redis.from_url(CACHE_REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
            redis_client.ping()  # Test connection
            # Redis is available, use it
            app.config['CACHE_TYPE'] = 'RedisCache'
            app.config['CACHE_REDIS_URL'] = CACHE_REDIS_URL
            app.config['CACHE_DEFAULT_TIMEOUT'] = CACHE_DEFAULT_TIMEOUT
            print("✅ Cache: Using Redis cache")
        except Exception as e:
            # Redis not available, use NullCache
            app.config['CACHE_TYPE'] = 'NullCache'
            app.config['CACHE_NO_NULL_WARNING'] = True
            error_msg = str(e)[:80] if len(str(e)) > 80 else str(e)
            print(f"⚠️  Cache: Redis unavailable ({error_msg}), using NullCache (no caching)")
    
    # Initialize cache
    cache.init_app(app)
    app.cache = cache  # Make cache accessible via app.cache
    
    # Initialize database
    db.init_app(app)
    
    # Initialize Flask-Migrate (if available)
    if migrate is not None:
        migrate.init_app(app, db)
    
    return app
