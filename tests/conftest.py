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

from database import db, init_db
from config import DATABASE_URL, REDIS_URL


@pytest.fixture(scope='session')
def app():
    """Create Flask app instance for testing."""
    # Import here to avoid circular dependencies
    from server import app as flask_app
    
    # Override config for testing
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key-for-pytest'
    
    # Use in-memory SQLite for testing
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


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

