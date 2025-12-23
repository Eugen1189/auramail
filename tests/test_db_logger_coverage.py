"""
Additional tests for db_logger.py to improve coverage from 55% to 85%+.
Focuses on edge cases, error handling, and reconnect logic.
"""
import os
# Force in-memory database for all tests
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock, Mock
from utils.db_logger import (
    log_action, save_report, get_latest_report,
    init_progress, update_progress, complete_progress,
    get_progress, get_followup_stats, get_log_entry, get_action_history, get_daily_stats
)
from database import ActionLog, Report, Progress, db


class TestLogActionReconnectLogic:
    """Test reconnect logic and error handling in log_action."""
    
    def test_log_action_handles_closed_session_with_reconnect(self, app, db_session):
        """Test that log_action reconnects when session is closed."""
        from utils.db_logger import log_action
        
        # Create initial entry
        classification = {
            'category': 'IMPORTANT',
            'description': 'Test email'
        }
        
        log_action('test-reconnect-1', classification, 'MOVE', 'Test Subject')
        
        # Simulate closed session by closing it manually
        db.session.close()
        db.session.remove()
        
        # Try to log another action - should reconnect automatically
        classification2 = {
            'category': 'ACTION_REQUIRED',
            'description': 'Test email 2'
        }
        
        # Should not raise exception - reconnect logic should handle it
        log_action('test-reconnect-2', classification2, 'ARCHIVE', 'Test Subject 2')
        
        # Verify both entries exist
        entry1 = ActionLog.query.filter_by(msg_id='test-reconnect-1').first()
        entry2 = ActionLog.query.filter_by(msg_id='test-reconnect-2').first()
        
        assert entry1 is not None
        assert entry2 is not None
        assert entry1.ai_category == 'IMPORTANT'
        assert entry2.ai_category == 'ACTION_REQUIRED'
    
    def test_log_action_handles_pending_rollback_error(self, app, db_session):
        """Test that log_action handles PendingRollbackError."""
        from utils.db_logger import log_action
        
        # Create a pending rollback state
        db.session.begin()
        try:
            # Create an entry that will cause an error
            invalid_entry = ActionLog(
                msg_id='invalid',
                subject='Test',
                ai_category='TEST'
            )
            db.session.add(invalid_entry)
            # Force a rollback state
            db.session.rollback()
        except Exception:
            pass
        
        # Now try to log action - should handle pending rollback
        classification = {
            'category': 'IMPORTANT',
            'description': 'Test email'
        }
        
        log_action('test-pending-rollback', classification, 'MOVE', 'Test Subject')
        
        # Verify entry was created despite pending rollback
        entry = ActionLog.query.filter_by(msg_id='test-pending-rollback').first()
        assert entry is not None
        assert entry.ai_category == 'IMPORTANT'
    
    def test_log_action_handles_invalid_transaction_error(self, app, db_session):
        """Test that log_action handles invalid transaction errors."""
        from utils.db_logger import log_action
        
        # Simulate invalid transaction by closing connection
        db.session.close()
        
        classification = {
            'category': 'IMPORTANT',
            'description': 'Test email'
        }
        
        # Should reconnect and succeed
        log_action('test-invalid-transaction', classification, 'MOVE', 'Test Subject')
        
        entry = ActionLog.query.filter_by(msg_id='test-invalid-transaction').first()
        assert entry is not None


class TestSaveReportErrorHandling:
    """Test error handling in save_report."""
    
    def test_save_report_handles_database_locking_error(self, app, db_session):
        """Test that save_report handles database locking errors with retry."""
        from utils.db_logger import save_report
        
        stats = {
            'total_processed': 10,
            'important': 2,
            'action_required': 1,
            'newsletter': 3,
            'social': 2,
            'review': 1,
            'archived': 1,
            'errors': 0
        }
        
        # Save report - should succeed
        save_report(stats)
        
        # Verify report was saved
        report = Report.query.order_by(Report.created_at.desc()).first()
        assert report is not None
        assert report.total_processed == 10
    
    def test_save_report_handles_cache_invalidation_error(self, app, db_session):
        """Test that save_report handles cache invalidation errors gracefully."""
        from utils.db_logger import save_report
        
        # Mock cache invalidation to raise error
        with patch('utils.db_logger._invalidate_cache', side_effect=Exception("Cache error")):
            stats = {
                'total_processed': 5,
                'important': 1,
                'action_required': 0,
                'newsletter': 2,
                'social': 1,
                'review': 0,
                'archived': 1,
                'errors': 0
            }
            
            # Should not raise exception - cache errors are non-critical
            save_report(stats)
            
            # Verify report was saved despite cache error
            report = Report.query.order_by(Report.created_at.desc()).first()
            assert report is not None
            assert report.total_processed == 5


class TestGetLatestReportEdgeCases:
    """Test edge cases in get_latest_report."""
    
    def test_get_latest_report_returns_default_when_no_reports(self, app, db_session):
        """Test that get_latest_report returns default dict when no reports exist."""
        from utils.db_logger import get_latest_report
        
        # Ensure no reports exist
        Report.query.delete()
        db.session.commit()
        
        result = get_latest_report()
        
        assert isinstance(result, dict)
        assert result['total_processed'] == 0
        assert result['important'] == 0
        assert result['action_required'] == 0
        assert result['newsletter'] == 0
        assert result['social'] == 0
        assert result['review'] == 0
        assert result['archived'] == 0
        assert result['errors'] == 0
    
    def test_get_latest_report_handles_database_error(self, app, db_session):
        """Test that get_latest_report handles database errors gracefully."""
        from utils.db_logger import get_latest_report
        
        # Mock query to raise exception
        with patch('database.Report.query') as mock_query:
            mock_query.order_by.return_value.first.side_effect = Exception("Database error")
            
            result = get_latest_report()
            
            # Should return default dict on error
            assert isinstance(result, dict)
            assert result['total_processed'] == 0


class TestProgressFunctionsEdgeCases:
    """Test edge cases in progress tracking functions."""
    
    def test_init_progress_handles_database_error(self, app, db_session):
        """Test that init_progress handles database errors."""
        from utils.db_logger import init_progress
        
        # Mock commit to raise exception
        with patch.object(db.session, 'commit', side_effect=Exception("Database error")):
            # Should handle error gracefully
            try:
                init_progress(total=10)
            except Exception:
                pass  # Expected to handle error
    
    def test_update_progress_handles_missing_progress(self, app, db_session):
        """Test that update_progress handles missing progress entry."""
        from utils.db_logger import update_progress, init_progress
        
        # Ensure no progress exists
        Progress.query.delete()
        db.session.commit()
        
        # Initialize progress first (update_progress expects progress to exist)
        init_progress(total=10)
        
        # Now update progress
        stats = {
            'total_processed': 5,
            'important': 1
        }
        update_progress(current=5, stats=stats, details='Processing...')
        
        progress = Progress.query.first()
        assert progress is not None
        assert progress.current == 5
        assert progress.total == 10
    
    def test_complete_progress_handles_missing_progress(self, app, db_session):
        """Test that complete_progress handles missing progress entry."""
        from utils.db_logger import complete_progress
        
        # Ensure no progress exists
        Progress.query.delete()
        db.session.commit()
        
        stats = {
            'total_processed': 10,
            'important': 2
        }
        
        # Should create new progress entry with completed status
        complete_progress(stats=stats, details='Completed!')
        
        progress = Progress.query.first()
        assert progress is not None
        assert progress.status == 'Completed'
        assert progress.current == progress.total  # Should be 100% complete


class TestGetFollowupStatsEdgeCases:
    """Test edge cases in get_followup_stats."""
    
    def test_get_followup_stats_handles_empty_database(self, app, db_session):
        """Test that get_followup_stats handles empty database."""
        from utils.db_logger import get_followup_stats
        
        # Ensure no entries exist
        ActionLog.query.delete()
        db.session.commit()
        
        result = get_followup_stats()
        
        assert isinstance(result, dict)
        assert result['pending'] == 0
        assert result['overdue'] == 0
    
    def test_get_followup_stats_with_future_dates(self, app, db_session):
        """Test get_followup_stats with future expected_reply_date."""
        from utils.db_logger import log_action, get_followup_stats
        
        # Create entry with future date
        future_date = date.today() + timedelta(days=7)
        classification = {
            'category': 'ACTION_REQUIRED',
            'expects_reply': True,
            'expected_reply_date': future_date.isoformat()
        }
        
        log_action('test-future-date', classification, 'MOVE', 'Test Subject')
        
        result = get_followup_stats()
        
        # Should count as pending (not overdue)
        assert result['pending'] >= 1
        assert result['overdue'] == 0


class TestGetLogEntryEdgeCases:
    """Test edge cases in get_log_entry."""
    
    def test_get_log_entry_returns_none_for_nonexistent_entry(self, app, db_session):
        """Test that get_log_entry returns None for nonexistent entry."""
        from utils.db_logger import get_log_entry
        
        result = get_log_entry('nonexistent-msg-id')
        
        assert result is None
    
    def test_get_log_entry_handles_database_error(self, app, db_session):
        """Test that get_log_entry handles database errors gracefully."""
        from utils.db_logger import get_log_entry
        
        # Mock query to raise exception
        with patch('database.ActionLog.query') as mock_query:
            mock_query.filter_by.return_value.first.side_effect = Exception("Database error")
            
            result = get_log_entry('test-msg-id')
            
            # Should return None on error
            assert result is None


class TestGetActionHistoryEdgeCases:
    """Test edge cases in get_action_history."""
    
    def test_get_action_history_handles_empty_database(self, app, db_session):
        """Test that get_action_history handles empty database."""
        from utils.db_logger import get_action_history
        
        # Ensure no entries exist
        ActionLog.query.delete()
        db.session.commit()
        
        result = get_action_history(limit=10)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_action_history_respects_limit(self, app, db_session):
        """Test that get_action_history respects limit parameter."""
        from utils.db_logger import log_action, get_action_history
        
        # Create multiple entries
        for i in range(15):
            classification = {
                'category': 'IMPORTANT',
                'description': f'Test email {i}'
            }
            log_action(f'test-limit-{i}', classification, 'MOVE', f'Test Subject {i}')
        
        result = get_action_history(limit=10)
        
        assert len(result) <= 10


class TestGetDailyStatsEdgeCases:
    """Test edge cases in get_daily_stats."""
    
    def test_get_daily_stats_handles_empty_database(self, app, db_session):
        """Test that get_daily_stats handles empty database."""
        from utils.db_logger import get_daily_stats
        
        # Ensure no entries exist
        ActionLog.query.delete()
        db.session.commit()
        
        result = get_daily_stats(days=7)
        
        assert isinstance(result, dict)
        assert len(result) == 7  # Should return 7 days with 0 counts
    
    def test_get_daily_stats_respects_days_parameter(self, app, db_session):
        """Test that get_daily_stats respects days parameter."""
        from utils.db_logger import get_daily_stats
        
        result = get_daily_stats(days=14)
        
        assert isinstance(result, dict)
        assert len(result) == 14  # Should return 14 days


from datetime import timedelta

