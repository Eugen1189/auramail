"""
Pytest configuration and shared fixtures for AuraMail tests.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from redis import Redis

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set TESTING environment variable BEFORE any imports
# This ensures app_factory.create_app() configures NullCache automatically
os.environ['TESTING'] = 'True'

# Mock Talisman before importing server to prevent HTTPS redirects in tests
# This must be done at module level before server is imported
from unittest.mock import MagicMock
if 'flask_talisman' not in sys.modules:
    flask_talisman_mock = MagicMock()
    flask_talisman_mock.Talisman = lambda *args, **kwargs: None
    sys.modules['flask_talisman'] = flask_talisman_mock

from database import db, init_db
from config import DATABASE_URL, REDIS_URL


@pytest.fixture(scope='session')
def app():
    """
    Create Flask app instance for testing.
    
    Cache is automatically configured as NullCache in app_factory.create_app()
    because TESTING=True is set in environment at module level.
    """
    # Import server here (TESTING is already set in environment at module level)
    # Talisman is already mocked at module level above
    from server import app as flask_app
    
    # Ensure testing mode is set (should already be set by app_factory)
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key-for-pytest'
    flask_app.config['FORCE_HTTPS'] = False  # Disable HTTPS for tests
    
    # Use in-memory SQLite for testing
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Verify cache is NullCache (app_factory should have set it automatically)
    # Cache should already be configured by app_factory when TESTING=True in environment
    if flask_app.config.get('CACHE_TYPE') != 'NullCache':
        # Fallback: reconfigure if not already set (should not happen)
        flask_app.cache.init_app(flask_app, config={
            'CACHE_TYPE': 'NullCache',
            'CACHE_NO_NULL_WARNING': True
        })
    
    # Add context for fixture (important for SQLAlchemy and other extensions)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        # Cleanup: drop tables
        db.drop_all()


@pytest.fixture
def client(app):
    """Create Flask test client."""
    # Test client automatically manages request context
    # No need for additional app context here since fixture 'app' handles it
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock_redis = MagicMock(spec=Redis)
    mock_redis.zremrangebyscore.return_value = 0
    mock_redis.zcard.return_value = 0
    mock_redis.zadd.return_value = 1
    mock_redis.expire.return_value = True
    return mock_redis


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini API client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"category": "REVIEW", "action": "ARCHIVE", "urgency": "MEDIUM", "description": "Test"}'
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_google_credentials():
    """Mock Google OAuth credentials."""
    return {
        'token': 'mock_token',
        'refresh_token': 'mock_refresh_token',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': 'mock_client_id',
        'client_secret': 'mock_client_secret',
        'scopes': ['https://www.googleapis.com/auth/gmail.modify']
    }

