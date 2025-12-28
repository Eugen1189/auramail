"""
Pytest configuration and shared fixtures for AuraMail tests.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from redis import Redis

# CRITICAL: Force in-memory database BEFORE any imports
# This prevents any file-based database from being used during tests
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set TESTING environment variable BEFORE any imports
# This ensures app_factory.create_app() configures NullCache automatically
os.environ['TESTING'] = 'True'

# Check for existing database file and warn if found
# This helps identify if tests are accidentally using file-based database
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_file = os.path.join(project_root, 'auramail.db')
if os.path.exists(db_file):
    import warnings
    warnings.warn(
        f"⚠️  WARNING: Database file {db_file} exists. "
        f"Tests should use in-memory database only. "
        f"Consider removing this file if tests fail. "
        f"Note: Tests will still use in-memory database due to forced configuration.",
        UserWarning
    )

@pytest.fixture(autouse=True)
def mock_sleep():
    """Mock time.sleep globally to speed up tests."""
    with patch('time.sleep') as mock_sleep:
        yield mock_sleep

# Mock Talisman before importing server to prevent HTTPS redirects in tests
# This must be done at module level before server is imported
from unittest.mock import MagicMock
if 'flask_talisman' not in sys.modules:
    flask_talisman_mock = MagicMock()
    flask_talisman_mock.Talisman = lambda *args, **kwargs: None
    sys.modules['flask_talisman'] = flask_talisman_mock

from database import db, init_db
from config import DATABASE_URL, REDIS_URL


@pytest.fixture(scope='session', autouse=True)
def cleanup_database_files():
    """
    Global cleanup fixture that removes any test database files before and after test session.
    
    This ensures no database files are left on disk that could cause locking issues.
    Scope='session' means it runs once before all tests and once after all tests complete.
    autouse=True ensures it runs automatically without needing to be explicitly requested.
    """
    import glob
    
    # List of potential test database files to clean up
    test_db_patterns = [
        'test_aura.db',
        'test_aura.db-journal',
        'test_aura.db-wal',
        'test_aura.db-shm',
        'auramail_test.db',
        'auramail_test.db-journal',
        'auramail_test.db-wal',
        'auramail_test.db-shm',
    ]
    
    # Get project root directory (parent of tests directory)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Clean up before test session starts
    for pattern in test_db_patterns:
        db_path = os.path.join(project_root, pattern)
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except (OSError, PermissionError):
                # File might be locked, try again later
                pass
    
    # Yield control to test session
    yield
    
    # Clean up after test session completes
    for pattern in test_db_patterns:
        db_path = os.path.join(project_root, pattern)
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except (OSError, PermissionError):
                # File might be locked, but tests should use in-memory DB anyway
                pass


@pytest.fixture(scope='function')
def app():
    """
    Create Flask app instance for testing with isolated in-memory database.
    
    Scope='function' ensures each test gets a fresh app instance and completely isolated
    in-memory database. This eliminates all database locking issues.
    
    Each test gets its own isolated in-memory SQLite database through:
    1. Function-scoped fixture (new app instance per test)
    2. poolclass=None (no connection pooling, each connection gets its own database)
    3. Engine disposal after each test (releases all connections)
    """
    # Import server here (TESTING is already set in environment at module level)
    # Talisman is already mocked at module level above
    from server import app as flask_app
    
    # Ensure testing mode is set (should already be set by app_factory)
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key-for-pytest'
    flask_app.config['FORCE_HTTPS'] = False  # Disable HTTPS for tests
    
    # CRITICAL: Force in-memory SQLite database for ALL tests
    # This MUST be sqlite:///:memory: to prevent database locking issues
    # We explicitly override any DATABASE_URL from config to ensure tests never use file-based databases
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Assert that we're using in-memory database (safety check)
    assert flask_app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:', \
        "Tests MUST use in-memory database. Found: {}".format(flask_app.config['SQLALCHEMY_DATABASE_URI'])
    
    # Critical: Disable connection pooling for in-memory SQLite
    # poolclass=None means no pooling - each connection gets its own isolated database
    # check_same_thread=False allows multi-threaded access (needed for tests)
    # timeout=60 increases wait time for database lock (prevents "database is locked" errors, increased for reliability)
    # isolation_level=None allows SQLAlchemy to manage transactions more flexibly (autocommit mode)
    # WAL mode allows concurrent reads without blocking writes
    flask_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': None,  # No pooling - each test gets fresh connection with isolated database
        'connect_args': {
            'check_same_thread': False,  # Allow multi-threaded access (needed for tests)
            'timeout': 60,  # Wait up to 60 seconds for database lock to be released (increased for reliability)
            'isolation_level': None  # Allows SQLAlchemy to manage transactions more flexibly (autocommit mode)
        }
    }
    
    # Dispose any existing engine before re-initializing
    # This ensures we start fresh for each test
    try:
        if hasattr(db, 'engine') and db.engine is not None:
            db.engine.dispose()
    except Exception:
        pass
    
    # Re-initialize database with new configuration for this test
    # This creates a new engine with in-memory database, ensuring complete isolation
    try:
        init_db(flask_app)
    except RuntimeError:
        # SQLAlchemy already registered on this app, which is expected since app_factory creates it.
        # We just need to ensure the engine reflects the new config (done by dispose above + new config)
        pass
    
    # CRITICAL: Force NullCache for all tests to prevent Redis/disk cache interactions
    # This eliminates cache-related delays and ensures tests are isolated
    if flask_app.config.get('CACHE_TYPE') != 'NullCache':
        # Force NullCache configuration
        flask_app.config['CACHE_TYPE'] = 'NullCache'
        flask_app.config['CACHE_NO_NULL_WARNING'] = True
        # Reinitialize cache with NullCache
        flask_app.cache.init_app(flask_app, config={
            'CACHE_TYPE': 'NullCache',
            'CACHE_NO_NULL_WARNING': True
        })
    
    # Assert that cache is NullCache (safety check)
    assert flask_app.config.get('CACHE_TYPE') == 'NullCache', \
        f"Tests MUST use NullCache. Found: {flask_app.config.get('CACHE_TYPE')}"
    
    # Add context for fixture (important for SQLAlchemy and other extensions)
    with flask_app.app_context():
        # CRITICAL: Create static connection for the test to keep database in memory
        # This ensures the in-memory database persists throughout the entire test
        static_connection = None
        try:
            # Create a static connection that will be kept alive during the test
            static_connection = db.engine.connect()
            # Bind this connection to the session for the duration of the test
            db.session.bind = static_connection
            
            # Initialize database tables for this test (fresh in-memory database)
            try:
                db.drop_all()
            except Exception:
                db.session.remove()
                try:
                    db.drop_all()
                except Exception:
                    pass
                    
            db.create_all()
            
            # Enable WAL mode for SQLite (allows concurrent reads without blocking writes)
            # Note: WAL mode doesn't work with in-memory databases, but this is safe to call
            # Set busy_timeout to 30 seconds (30000 milliseconds) to wait for lock release
            # This prevents "database is locked" errors during intensive write operations
            try:
                db.session.execute(db.text('PRAGMA journal_mode=WAL'))
                db.session.execute(db.text('PRAGMA busy_timeout = 30000'))
                db.session.commit()
            except Exception:
                # If WAL mode fails (e.g., in-memory DB), continue anyway
                db.session.rollback()
            
            yield flask_app
        finally:
            # CRITICAL: Explicit rollback in finally block to avoid PendingRollbackError
            # This ensures clean state for next test
            try:
                # First, rollback any pending transactions
                db.session.rollback()
            except Exception:
                # If rollback fails, try to close session
                try:
                    db.session.close()
                except Exception:
                    pass
            
            # Then remove session to prevent database locking
            # This ensures each test starts with a clean session state
            try:
                db.session.remove()
            except Exception:
                pass
            
            # Close static connection if it was created
            if static_connection:
                try:
                    static_connection.close()
                except Exception:
                    pass
            
            # Final cleanup: expire all objects to clear session state
            try:
                db.session.expire_all()
            except Exception:
                pass
        
        # Remove session BEFORE drop_all to release locks
        try:
            db.session.remove()
        except Exception:
            pass
        
        # Drop all tables
        try:
            db.drop_all()
        except Exception:
            pass
        
        # Final cleanup: ensure session is closed
        finally:
            # Always remove session to prevent connection leaks
            try:
                db.session.rollback()  # Rollback any pending changes
            except Exception:
                pass
            
            try:
                db.session.remove()  # Remove session from registry
            except Exception:
                pass
            
            # Explicitly close session to ensure all connections are released
            try:
                if hasattr(db.session, 'close'):
                    db.session.close()
            except Exception:
                pass
            
            # Dispose engine to release all connections
            try:
                if hasattr(db, 'engine') and db.engine is not None:
                    db.engine.dispose()
            except Exception:
                pass


@pytest.fixture(scope='function', autouse=True)
def db_session(app):
    """
    Create isolated database session with transaction rollback for each test.
    
    BULLETPROOF FIXTURE: Absolutely guaranteed cleanup to prevent any state leakage.
    
    Scope='function' with autouse=True ensures this fixture runs for every test.
    
    Since app fixture is function-scoped with unique in-memory database per test,
    this fixture adds an extra layer of transaction isolation to ensure complete cleanup.
    
    For Flask-SQLAlchemy with in-memory SQLite:
    1. Each test gets its own app instance (function-scoped)
    2. Each app instance has its own isolated in-memory database (poolclass=None)
    3. This fixture provides transaction rollback for additional safety
    4. Engine is disposed after each test to release all connections
    
    BULLETPROOF CLEANUP STRATEGY:
    - BEFORE TEST: Remove any existing session to ensure clean state
    - AFTER TEST: Rollback all transactions, remove session, drop all tables
    - FINALLY BLOCK: Guaranteed cleanup even if test fails
    """
    with app.app_context():
        # BEFORE TEST: ABSOLUTE CLEAN STATE
        # CRITICAL: This MUST happen before ANY test runs to prevent "poisoned" sessions
        # Order matters: remove -> rollback -> create_all
        
        # Step 1: Remove any existing session FIRST (clears registry)
        try:
            db.session.remove()
        except Exception:
            pass
        
        # Step 2: Rollback any pending transactions (clears transaction state)
        try:
            db.session.rollback()
        except Exception:
            pass
        
        # Step 3: Ensure tables exist (create fresh tables for this test)
        try:
            db.create_all()
        except Exception:
            pass
        
        # Yield session - test runs here
        try:
            yield db.session
        finally:
            # AFTER TEST: BULLETPROOF CLEANUP
            # CRITICAL: This MUST happen in finally block to ensure cleanup even if test fails
            # Order matters: expire_all -> rollback -> drop_all -> remove -> final cleanup
            
            # Step 0: Expire all objects FIRST to clear any pending state
            # This prevents PendingRollbackError by clearing object state before rollback
            try:
                db.session.expire_all()
            except Exception:
                pass
            
            # Step 1: HARD rollback - cancel any pending transactions FIRST
            # This MUST happen before any other operations to avoid PendingRollbackError
            try:
                # Check if session is active before rollback
                if db.session.is_active:
                    db.session.rollback()
            except Exception as rollback_err:
                # If rollback fails, try to close session
                try:
                    if hasattr(db.session, 'close'):
                        db.session.close()
                except Exception:
                    pass
                # Log but don't fail - we'll continue cleanup
                print(f"⚠️ db_session fixture: Rollback warning: {rollback_err}")
            
            # Step 2: Drop all tables (before removing session)
            try:
                db.drop_all()
            except Exception as drop_err:
                # If drop_all fails, try rollback again
                try:
                    if db.session.is_active:
                        db.session.rollback()
                except Exception:
                    pass
                # Log but don't fail
                print(f"⚠️ db_session fixture: Drop_all warning: {drop_err}")
            
            # Step 3: HARD remove - completely close connection
            # This ensures session is completely removed from registry
            # CRITICAL: This prevents "poisoned" sessions from affecting next test
            try:
                db.session.remove()
            except Exception:
                pass
            
            # Step 4: Final cleanup - ensure session is completely closed
            # This is a safety net in case something was missed
            try:
                # Only try if session still exists (may have been removed in step 3)
                if hasattr(db.session, 'close'):
                    db.session.close()
            except Exception:
                pass
            
            # Step 5: Final expire_all to ensure clean state
            try:
                db.session.expire_all()
            except Exception:
                pass


@pytest.fixture
def client(app):
    """
    Create Flask test client with isolated database session and mocked authentication.
    
    Uses db_session fixture (autouse=True) and function-scoped app fixture
    to ensure each test runs in an isolated in-memory database.
    
    Mocks OAuth credentials in session to prevent 302 redirects to /authorize.
    """
    import json
    from datetime import datetime, timedelta
    
    # Create mock credentials JSON for testing
    # This prevents 302 redirects to /authorize in tests
    mock_credentials = {
        'token': 'mock_access_token',
        'refresh_token': 'mock_refresh_token',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': 'mock_client_id',
        'client_secret': 'mock_client_secret',
        'scopes': ['https://www.googleapis.com/auth/gmail.readonly'],
        'expiry': (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }
    
    with app.test_client() as client:
        # Set up session with mock credentials before each request
        with client.session_transaction() as sess:
            sess['credentials'] = json.dumps(mock_credentials)
            sess.permanent = True
        
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

