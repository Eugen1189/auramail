"""
Extended edge case tests for follow-up monitoring tasks.
Tests various scenarios for daily_followup_check and process_sent_email_task.
"""
import pytest
import json
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
from app_factory import create_app
from database import db, ActionLog


@pytest.fixture()
def app_ctx():
    """Create Flask app with database context and transaction isolation for each test."""
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
        # Clean database before each test
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


class DummyDrafts:
    def __init__(self, store):
        self.store = store
        self.create_error = None

    def create(self, userId, body):
        if self.create_error:
            raise self.create_error
        draft_id = f"draft-{len(self.store)+1}"
        self.store.append({'userId': userId, 'body': body, 'id': draft_id})
        return DummyExec({'id': draft_id})


class DummyMessages:
    def __init__(self):
        self.calls = []
        self.get_error = None

    def get(self, userId, id, format):
        if self.get_error:
            raise self.get_error
        self.calls.append({'userId': userId, 'id': id, 'format': format})
        return DummyExec({
            'id': id,
            'payload': {'headers': [{'name': 'To', 'value': 'test@example.com'}]},
            'snippet': 'Original email content'
        })


class DummyUsers:
    def __init__(self, drafts_store):
        self._drafts_store = drafts_store
        self._messages = DummyMessages()
        self._drafts = DummyDrafts(drafts_store)

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


class TestDailyFollowupCheckEdgeCases:
    """Edge case tests for daily_followup_check."""
    
    def test_followup_already_sent(self, app_ctx):
        """Test that follow-ups already sent are skipped."""
        from tasks import daily_followup_check
        
        # Create follow-up that was already sent
        overdue = ActionLog(
            msg_id="test-already-sent-m1",
            subject="Already Followed Up",
            ai_category="ACTION_REQUIRED",
            action_taken="MOVE",
            is_followup_pending=True,
            expected_reply_date=date.today() - timedelta(days=2),
            followup_sent=True,  # Already sent
            reason="",
            details={}
        )
        db.session.add(overdue)
        db.session.commit()
        
        gmail = DummyService()
        result = daily_followup_check(credentials_json=None, gmail_service=gmail)
        
        assert result['status'] == 'success'
        # Function only counts entries that match criteria (is_followup_pending=True, followup_sent=False, expected_reply_date <= today)
        # Since followup_sent=True, this entry won't be in the query result
        assert result['checked'] == 0  # No entries match criteria
        assert result['drafts_created'] == []  # No drafts created
        assert len(gmail.drafts_store) == 0
    
    def test_followup_not_pending(self, app_ctx):
        """Test that non-pending follow-ups are skipped."""
        from tasks import daily_followup_check
        
        # Create entry that is not pending
        not_pending = ActionLog(
            msg_id="test-not-pending-m2",
            subject="Not Pending",
            ai_category="ACTION_REQUIRED",
            action_taken="MOVE",
            is_followup_pending=False,  # Not pending
            expected_reply_date=date.today() - timedelta(days=1),
            followup_sent=False,
            reason="",
            details={}
        )
        db.session.add(not_pending)
        db.session.commit()
        
        gmail = DummyService()
        result = daily_followup_check(credentials_json=None, gmail_service=gmail)
        
        assert result['status'] == 'success'
        # Function filters by is_followup_pending=True, so this entry won't be in query
        assert result['checked'] == 0  # No entries match criteria
        assert result['drafts_created'] == []
    
    def test_followup_future_date(self, app_ctx):
        """Test that follow-ups with future dates are skipped."""
        from tasks import daily_followup_check
        
        # Create follow-up with future date
        future = ActionLog(
            msg_id="test-future-date-m3",
            subject="Future Follow-up",
            ai_category="ACTION_REQUIRED",
            action_taken="MOVE",
            is_followup_pending=True,
            expected_reply_date=date.today() + timedelta(days=5),  # Future
            followup_sent=False,
            reason="",
            details={}
        )
        db.session.add(future)
        db.session.commit()
        
        gmail = DummyService()
        result = daily_followup_check(credentials_json=None, gmail_service=gmail)
        
        assert result['status'] == 'success'
        # Function filters by expected_reply_date <= today, so future dates are excluded
        assert result['checked'] == 0  # No entries match criteria (future date excluded)
        assert result['drafts_created'] == []  # Not overdue yet
    
    def test_followup_missing_expected_date(self, app_ctx):
        """Test that follow-ups without expected_reply_date are handled."""
        from tasks import daily_followup_check
        
        # Create follow-up without expected_reply_date
        no_date = ActionLog(
            msg_id="test-no-date-m4",
            subject="No Date",
            ai_category="ACTION_REQUIRED",
            action_taken="MOVE",
            is_followup_pending=True,
            expected_reply_date=None,  # No date
            followup_sent=False,
            reason="",
            details={}
        )
        db.session.add(no_date)
        db.session.commit()
        
        gmail = DummyService()
        result = daily_followup_check(credentials_json=None, gmail_service=gmail)
        
        # Function filters by expected_reply_date.isnot(None), so entries without date are excluded
        assert result['status'] == 'success'
        assert result['checked'] == 0  # No entries match criteria (None date excluded)
        assert result['drafts_created'] == []
    
    def test_followup_draft_creation_error(self, app_ctx):
        """Test handling of draft creation errors."""
        from tasks import daily_followup_check
        
        # Create overdue follow-up
        overdue = ActionLog(
            msg_id="test-draft-error-m5",
            subject="Error Test",
            ai_category="ACTION_REQUIRED",
            action_taken="MOVE",
            is_followup_pending=True,
            expected_reply_date=date.today() - timedelta(days=1),
            followup_sent=False,
            reason="",
            details={}
        )
        db.session.add(overdue)
        db.session.commit()
        
        gmail = DummyService()
        # Simulate draft creation error
        gmail.users().drafts().create_error = Exception("Draft creation failed")
        
        result = daily_followup_check(credentials_json=None, gmail_service=gmail)
        
        # Should handle error gracefully
        assert result['status'] == 'success' or 'error' in result.get('status', '')
        # Entry should not be marked as sent if draft failed
        # Reload entry from database since session might have been cleared
        entry = ActionLog.query.filter_by(msg_id="test-draft-error-m5").first()
        assert entry is not None
        assert entry.followup_sent is False
    
    def test_followup_multiple_overdue(self, app_ctx):
        """Test handling multiple overdue follow-ups."""
        from tasks import daily_followup_check
        
        # Create multiple overdue follow-ups
        for i in range(3):
            overdue = ActionLog(
                msg_id=f"test-multiple-overdue-m{i+6}",
                subject=f"Overdue {i+1}",
                ai_category="ACTION_REQUIRED",
                action_taken="MOVE",
                is_followup_pending=True,
                expected_reply_date=date.today() - timedelta(days=i+1),
                followup_sent=False,
                reason="",
                details={}
            )
            db.session.add(overdue)
        db.session.commit()
        
        gmail = DummyService()
        result = daily_followup_check(credentials_json=None, gmail_service=gmail)
        
        assert result['status'] == 'success'
        assert result['checked'] == 3
        assert len(result['drafts_created']) == 3
        assert len(gmail.drafts_store) == 3
    
    def test_followup_mixed_scenarios(self, app_ctx):
        """Test mixed scenarios: some overdue, some future, some already sent."""
        from tasks import daily_followup_check
        
        # CRITICAL FIX: Калібрування логіки LibrarianAgent (2 помилки)
        # Очистити базу даних та таблицю action_logs перед запуском сценарію
        # Це гарантує, що LibrarianAgent не відфільтрує тестові листи
        # Примусове очищення таблиці action_logs перед початком
        
        # CRITICAL FIX: Використовуємо no_autoflush для запобігання передчасному flush
        # Очистити всі записи з action_logs перед додаванням нових
        ActionLog.query.delete()
        db.session.commit()
        db.session.expunge_all()  # CRITICAL FIX: Очищаємо всі об'єкти з сесії
        
        # Overdue and pending
        overdue1 = ActionLog(
            msg_id="test-mixed-overdue-m10",
            subject="Overdue 1",
            ai_category="ACTION_REQUIRED",
            action_taken="MOVE",
            is_followup_pending=True,
            expected_reply_date=date.today() - timedelta(days=2),
            followup_sent=False,
            reason="",
            details={}
        )
        
        # Already sent
        sent = ActionLog(
            msg_id="test-mixed-sent-m11",
            subject="Already Sent",
            ai_category="ACTION_REQUIRED",
            action_taken="MOVE",
            is_followup_pending=True,
            expected_reply_date=date.today() - timedelta(days=1),
            followup_sent=True,
            reason="",
            details={}
        )
        
        # Future date
        future = ActionLog(
            msg_id="test-mixed-future-m12",
            subject="Future",
            ai_category="ACTION_REQUIRED",
            action_taken="MOVE",
            is_followup_pending=True,
            expected_reply_date=date.today() + timedelta(days=3),
            followup_sent=False,
            reason="",
            details={}
        )
        
        db.session.add_all([overdue1, sent, future])
        db.session.commit()
        
        # CRITICAL FIX: Ensure entries are committed and visible
        # daily_followup_check uses @ensure_app_context, which will reuse existing app context
        # So entries should be visible if we're in the same app context
        db.session.commit()
        db.session.flush()
        
        # Verify entries exist before calling daily_followup_check
        all_entries = ActionLog.query.all()
        assert len(all_entries) == 3, f"Expected 3 entries, got {len(all_entries)}"
        
        # Verify overdue1 exists and matches criteria
        overdue_query = ActionLog.query.filter(
            ActionLog.is_followup_pending.is_(True),
            ActionLog.followup_sent.is_(False),
            ActionLog.expected_reply_date.isnot(None),
            ActionLog.expected_reply_date <= date.today()
        ).all()
        assert len(overdue_query) == 1, f"Expected 1 overdue entry, got {len(overdue_query)}. Entries: {[e.msg_id for e in overdue_query]}"
        
        # CRITICAL FIX: daily_followup_check uses @ensure_app_context which will reuse existing app context
        # Since we're already in app_ctx.app_context(), it should work correctly
        gmail = DummyService()
        result = daily_followup_check(credentials_json=None, gmail_service=gmail)
        
        assert result['status'] == 'success'
        # Function only counts entries matching: is_followup_pending=True, followup_sent=False, expected_reply_date <= today
        # Only overdue1 matches all criteria
        assert result['checked'] == 1, f"Expected 1 checked entry, got {result['checked']}"  # Only overdue1 matches criteria
        # Only overdue1 should create a draft
        assert len(result['drafts_created']) == 1, f"Expected 1 draft, got {len(result['drafts_created'])}"
        assert len(gmail.drafts_store) == 1, f"Expected 1 draft in store, got {len(gmail.drafts_store)}"


class TestProcessSentEmailTaskEdgeCases:
    """Edge case tests for process_sent_email_task."""
    
    def test_process_sent_email_missing_message(self, app_ctx):
        """Test process_sent_email_task handles missing message."""
        from tasks import process_sent_email_task
        
        class DummyServiceError:
            def users(self):
                return self
            def messages(self):
                return self
            def get(self, userId, id, format):
                raise Exception("Message not found")
        
        creds_json = json.dumps({
            "token": "x",
            "refresh_token": "y",
            "token_uri": "https://example.com",
            "client_id": "c",
            "client_secret": "s",
            "scopes": ["https://www.googleapis.com/auth/gmail.modify"]
        })
        
        with patch('tasks.build_google_services') as mock_build:
            mock_build.return_value = (DummyServiceError(), None)
            with patch('tasks.get_gemini_client'):
                with patch('tasks.detect_expected_reply_with_gemini') as mock_detect:
                    mock_detect.return_value = {"expects_reply": False, "expected_reply_date": ""}
                    result = process_sent_email_task(creds_json, "nonexistent-msg", "Test Subject", "Test content")
                    
                    # CRITICAL FIX: Функція обробляє помилки fetch gracefully
                    # Якщо subject та content надані, функція використовує їх і повертає 'success'
                    # Навіть якщо Gmail fetch не вдався, функція працює з наданими даними
                    assert result['status'] == 'success'
                    # Entry should be created since subject/content were provided
                    entry = ActionLog.query.filter_by(msg_id="nonexistent-msg").first()
                    assert entry is not None
    
    def test_process_sent_email_gemini_error(self, app_ctx):
        """Test process_sent_email_task handles Gemini API errors."""
        from tasks import process_sent_email_task
        
        class DummyService:
            def users(self):
                return self
            def messages(self):
                return self
            def get(self, userId, id, format):
                return DummyExec({
                    'id': id,
                    'snippet': 'Test email',
                    'payload': {'headers': [{'name': 'Subject', 'value': 'Test'}]}
                })
        
        creds_json = json.dumps({
            "token": "x",
            "refresh_token": "y",
            "token_uri": "https://example.com",
            "client_id": "c",
            "client_secret": "s",
            "scopes": ["https://www.googleapis.com/auth/gmail.modify"]
        })
        
        def fake_detect_error(client, content):
            raise Exception("Gemini API error")
        
        with patch('tasks.build_google_services') as mock_build:
            mock_build.return_value = (DummyService(), None)
            with patch('tasks.get_gemini_client'):
                with patch('tasks.detect_expected_reply_with_gemini', fake_detect_error):
                    result = process_sent_email_task(creds_json, "test-msg", None, None)
                    
                    assert result['status'] == 'error' or 'error' in result
    
    def test_process_sent_email_no_reply_expected(self, app_ctx):
        """Test process_sent_email_task when no reply is expected."""
        from tasks import process_sent_email_task
        
        # CRITICAL FIX: Калібрування логіки LibrarianAgent
        # Очистити базу даних та таблицю action_logs перед запуском сценарію
        # Це гарантує, що LibrarianAgent не відфільтрує тестові листи
        ActionLog.query.delete()
        db.session.commit()
        db.session.expunge_all()  # CRITICAL FIX: Очищаємо всі об'єкти з сесії
        
        class DummyService:
            def users(self):
                return self
            def messages(self):
                return self
            def get(self, userId, id, format):
                return DummyExec({
                    'id': id,
                    'snippet': 'Just a notification',
                    'payload': {'headers': [{'name': 'Subject', 'value': 'Notification'}]}
                })
        
        def fake_detect_no_reply(client, content):
            return {
                "expects_reply": False,
                "expected_reply_date": None,
                "confidence": "HIGH"
            }
        
        creds_json = json.dumps({
            "token": "x",
            "refresh_token": "y",
            "token_uri": "https://example.com",
            "client_id": "c",
            "client_secret": "s",
            "scopes": ["https://www.googleapis.com/auth/gmail.modify"]
        })
        
        with patch('tasks.build_google_services') as mock_build:
            mock_build.return_value = (DummyService(), None)
            with patch('tasks.get_gemini_client'):
                with patch('tasks.detect_expected_reply_with_gemini', fake_detect_no_reply):
                    result = process_sent_email_task(creds_json, "test-msg-2", None, None)
                    
                    assert result['status'] == 'success'
                    entry = ActionLog.query.filter_by(msg_id="test-msg-2").first()
                    assert entry is not None
                    assert entry.is_followup_pending is False
                    assert entry.expected_reply_date is None

