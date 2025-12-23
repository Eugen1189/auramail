import json
from datetime import date, timedelta

import pytest

from app_factory import create_app
from database import db, ActionLog
from tasks import daily_followup_check, process_sent_email_task
from utils.gemini_processor import detect_expected_reply_with_gemini


class DummyDrafts:
    def __init__(self, store):
        self.store = store

    def create(self, userId, body):
        draft_id = f"draft-{len(self.store)+1}"
        self.store.append({'userId': userId, 'body': body, 'id': draft_id})
        return DummyExec({'id': draft_id})


class DummyMessages:
    def __init__(self):
        self.calls = []

    def get(self, userId, id, format):
        self.calls.append({'userId': userId, 'id': id, 'format': format})
        return DummyExec({'id': id, 'payload': {'headers': [{'name': 'To', 'value': 'test@example.com'}]}, 'snippet': 'Original'})


class DummyUsers:
    def __init__(self, drafts_store):
        self._drafts_store = drafts_store
        self._messages = DummyMessages()
        self._drafts = DummyDrafts(self._drafts_store)

    def messages(self):
        return self._messages

    def drafts(self):
        return self._drafts


class DummyService:
    def __init__(self):
        self.drafts_store = []
        self._users = DummyUsers(self.drafts_store)

    def users(self):
        return self._users


class DummyExec:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


@pytest.fixture()
def app_ctx():
    """Create Flask app with database context and transaction isolation."""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    
    # Add timeout and isolation_level to prevent database locking
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': None,
        'connect_args': {
            'check_same_thread': False,
            'timeout': 30,
            'isolation_level': None  # Allows SQLAlchemy to manage transactions more flexibly
        }
    }
    
    # Re-initialize database with new configuration
    try:
        from database import init_db
        init_db(app)
    except Exception:
        pass
    
    with app.app_context():
        try:
            db.drop_all()
        except Exception:
            db.session.rollback()
            db.session.remove()
        db.create_all()
        
        # Enable WAL mode for SQLite (if not in-memory)
        try:
            db.session.execute(db.text('PRAGMA journal_mode=WAL'))
            db.session.commit()
        except Exception:
            db.session.rollback()
        
        yield app
        
        # Cleanup: ensure all transactions are closed
        try:
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        
        # Remove session to release locks
        try:
            db.session.remove()
        except Exception:
            pass
        
        # Drop all tables
        try:
            db.drop_all()
        except Exception:
            pass
        
        # Final cleanup
        finally:
            try:
                db.session.remove()
            except Exception:
                pass
            try:
                if hasattr(db, 'engine') and db.engine is not None:
                    db.engine.dispose()
            except Exception:
                pass


def test_daily_followup_creates_draft_and_marks_sent(app_ctx):
    # Arrange
    today = date.today()
    pending = ActionLog(
        msg_id="test-followup-monitor-m1",
        subject="Subject",
        ai_category="ACTION_REQUIRED",
        action_taken="MOVE",
        is_followup_pending=True,
        expected_reply_date=today - timedelta(days=1),
        followup_sent=False,
        reason="",
        details={}
    )
    db.session.add(pending)
    db.session.flush()  # Use flush instead of commit for test isolation

    gmail = DummyService()

    # Act
    result = daily_followup_check(credentials_json=None, gmail_service=gmail)

    # Assert
    assert result['status'] == 'success'
    assert result['checked'] == 1
    assert len(result['drafts_created']) == 1
    
    # Refresh pending entry
    pending = ActionLog.query.filter_by(msg_id="test-followup-monitor-m1").first()
    assert pending is not None
    assert pending.followup_sent is True
    assert pending.is_followup_pending is False
    assert 'followup_draft_id' in pending.details
    assert gmail.drafts_store[0]['body']['message']['raw']  # raw draft exists


def test_daily_followup_no_pending_returns_success(app_ctx):
    gmail = DummyService()
    result = daily_followup_check(credentials_json=None, gmail_service=gmail)
    assert result['status'] == 'success'
    assert result['checked'] == 0
    assert result['drafts_created'] == []


def test_process_sent_email_task_sets_followup_flags(monkeypatch, app_ctx):
    # Prepare dummy gmail service and monkeypatch build_google_services
    class DummySentService:
        def __init__(self):
            self.calls = []

        def users(self):
            return self

        def messages(self):
            return self

        def get(self, userId, id, format):
            self.calls.append({'userId': userId, 'id': id, 'format': format})
            return DummyExec({
                'id': id,
                'snippet': 'Please reply by 2025-12-31',
                'payload': {'headers': [{'name': 'Subject', 'value': 'Follow up needed'}]}
            })

    dummy_service = DummySentService()

    def fake_build_google_services(creds):
        return dummy_service, None

    def fake_detect_expected_reply(client, content):
        return {
            "expects_reply": True,
            "expected_reply_date": "2025-12-31",
            "confidence": "HIGH"
        }

    monkeypatch.setattr('tasks.build_google_services', fake_build_google_services)
    monkeypatch.setattr('tasks.get_gemini_client', lambda: object())
    monkeypatch.setattr('tasks.detect_expected_reply_with_gemini', fake_detect_expected_reply)
    
    # Ensure session is clean
    db.session.remove()

    creds_json = json.dumps({"token": "x", "refresh_token": "y", "token_uri": "https://example.com", "client_id": "c", "client_secret": "s", "scopes": ["https://www.googleapis.com/auth/gmail.modify"]})

    result = process_sent_email_task(creds_json, "test-followup-monitor-sent-1", None, None)
    assert result['status'] == 'success'
    entry = ActionLog.query.filter_by(msg_id="test-followup-monitor-sent-1").first()
    assert entry is not None
    assert entry.is_followup_pending is True
    assert entry.expected_reply_date.isoformat() == "2025-12-31"

