"""
Extended Unit and Integration tests for database logger.
Tests all logging, progress tracking, and report functions.
"""
import pytest
from datetime import datetime, timedelta
from database import db, ActionLog, Progress, Report


class TestProgressTracking:
    """Test suite for progress tracking functions."""
    
    def test_init_progress_creates_new_progress(self, app):
        """Test that init_progress creates a new progress entry."""
        from utils.db_logger import init_progress, get_progress
        
        with app.app_context():
            init_progress(total=100)
            
            progress = get_progress()
            
            assert progress is not None
            assert progress['total'] == 100
            assert progress['current'] == 0
            assert progress['status'] == 'Starting...'
    
    def test_update_progress_updates_existing_entry(self, app):
        """Test that update_progress updates the existing progress entry."""
        from utils.db_logger import init_progress, update_progress, get_progress
        
        with app.app_context():
            init_progress(total=100)
            stats = {'processed': 50, 'errors': 2}
            update_progress(50, stats, "Processing email 50/100")
            
            progress = get_progress()
            
            assert progress['current'] == 50
            assert progress['stats'] == stats
            assert progress['details'] == "Processing email 50/100"
    
    def test_complete_progress_marks_as_complete(self, app):
        """Test that complete_progress marks progress as completed."""
        from utils.db_logger import init_progress, complete_progress, get_progress
        
        with app.app_context():
            init_progress(total=100)
            final_stats = {
                'total_processed': 100,
                'important': 20,
                'archived': 10
            }
            complete_progress(final_stats)
            
            progress = get_progress()
            
            assert progress['status'] == 'Completed'
            assert progress['current'] == 100
            assert progress['stats'] == final_stats
    
    def test_get_progress_returns_default_when_no_progress(self, app):
        """Test that get_progress returns default dict when no progress exists."""
        from utils.db_logger import get_progress
        
        with app.app_context():
            # Clear any existing progress
            Progress.query.delete()
            db.session.commit()
            
            progress = get_progress()
            
            # Function returns default dict, not None
            assert progress is not None
            assert isinstance(progress, dict)
            assert progress.get('total') == 0
            assert progress.get('status') == 'Idle'


class TestActionHistory:
    """Test suite for action history functions."""
    
    def test_get_action_history_returns_recent_actions(self, app):
        """Test that get_action_history returns recent actions."""
        from utils.db_logger import log_action, get_action_history
        
        with app.app_context():
            # Create some test actions
            for i in range(5):
                log_action(
                    msg_id=f'test-msg-{i}',
                    classification={'category': 'IMPORTANT', 'action': 'MOVE'},
                    action_taken='MOVED to AI_IMPORTANT',
                    subject=f'Test Email {i}'
                )
            
            history = get_action_history(limit=3)
            
            assert len(history) == 3
            assert all(isinstance(action, dict) for action in history)
            # get_action_history reverses entries to show oldest first
            # So first entry should be test-msg-0 (oldest), last should be test-msg-4 (newest)
            assert history[-1]['msg_id'] == 'test-msg-4'  # Most recent is last
            assert history[0]['msg_id'] == 'test-msg-2'  # Oldest of last 3 is first
    
    def test_get_action_history_returns_empty_when_no_actions(self, app):
        """Test that get_action_history returns empty list when no actions exist."""
        from utils.db_logger import get_action_history
        
        with app.app_context():
            # Clear any existing actions
            ActionLog.query.delete()
            db.session.commit()
            
            history = get_action_history()
            
            assert history == []


class TestDailyStats:
    """Test suite for daily statistics functions."""
    
    def test_get_daily_stats_calculates_stats_by_date(self, app):
        """Test that get_daily_stats calculates statistics grouped by date."""
        from utils.db_logger import log_action, get_daily_stats
        
        with app.app_context():
            # Clear existing logs
            ActionLog.query.delete()
            db.session.commit()
            
            # Create actions for different dates
            # Note: We can't easily mock dates, so we'll create actions and check grouping
            for i in range(3):
                log_action(
                    msg_id=f'daily-test-{i}',
                    classification={'category': 'IMPORTANT', 'action': 'MOVE'},
                    action_taken='MOVED to AI_IMPORTANT',
                    subject=f'Daily Test {i}'
                )
            
            stats = get_daily_stats(days=7)
            
            assert isinstance(stats, dict)
            # Should have at least one date entry
            assert len(stats) > 0
            # All values should be integers
            assert all(isinstance(count, int) for count in stats.values())
    
    def test_get_daily_stats_handles_empty_history(self, app):
        """Test that get_daily_stats handles empty action history."""
        from utils.db_logger import get_daily_stats
        
        with app.app_context():
            # Clear any existing actions
            ActionLog.query.delete()
            db.session.commit()
            
            stats = get_daily_stats(days=7)
            
            assert isinstance(stats, dict)
            # Should return empty dict or dict with zero counts
            assert all(count == 0 for count in stats.values()) if stats else True


class TestReportFunctions:
    """Test suite for report saving and retrieval."""
    
    def test_save_report_creates_new_report(self, app):
        """Test that save_report creates a new report entry."""
        from utils.db_logger import save_report, get_latest_report
        
        with app.app_context():
            stats = {
                'total_processed': 100,
                'important': 25,
                'action_required': 15,
                'newsletter': 30,
                'social': 10,
                'review': 10,
                'archived': 10,
                'errors': 0
            }
            
            save_report(stats)
            
            report = get_latest_report()
            
            assert report is not None
            assert report['total_processed'] == 100
            assert report['important'] == 25
            assert report['archived'] == 10
    
    def test_get_latest_report_returns_most_recent(self, app):
        """Test that get_latest_report returns the most recent report."""
        from utils.db_logger import save_report, get_latest_report
        
        with app.app_context():
            # Create two reports
            save_report({'total_processed': 50, 'important': 10, 'action_required': 5,
                        'newsletter': 20, 'social': 5, 'review': 5, 'archived': 5, 'errors': 0})
            
            save_report({'total_processed': 100, 'important': 25, 'action_required': 15,
                        'newsletter': 30, 'social': 10, 'review': 10, 'archived': 10, 'errors': 0})
            
            report = get_latest_report()
            
            assert report['total_processed'] == 100  # Most recent
    
    def test_get_latest_report_returns_default_when_no_reports(self, app):
        """Test that get_latest_report returns default dict when no reports exist."""
        from utils.db_logger import get_latest_report
        
        with app.app_context():
            # Clear any existing reports
            Report.query.delete()
            db.session.commit()
            
            report = get_latest_report()
            
            # Function returns default dict with zeros, not None
            assert report is not None
            assert isinstance(report, dict)
            assert report.get('total_processed') == 0


class TestLogActionExtended:
    """Extended test suite for log_action function."""
    
    def test_log_action_creates_entry_with_full_details(self, app):
        """Test that log_action creates entry with all classification details."""
        from utils.db_logger import log_action, get_log_entry
        
        with app.app_context():
            classification = {
                'category': 'ACTION_REQUIRED',
                'action': 'MOVE',
                'label_name': 'AI_ACTION_REQUIRED',
                'description': 'Email requires action',
                'urgency': 'high',
                'extracted_entities': {
                    'due_date': '2025-12-31',
                    'location': 'Office'
                }
            }
            
            log_action(
                msg_id='test-full-details',
                classification=classification,
                action_taken='MOVED to AI_ACTION_REQUIRED',
                subject='Action Required Email'
            )
            
            entry = get_log_entry('test-full-details')
            
            assert entry is not None
            assert entry['ai_category'] == 'ACTION_REQUIRED'
            assert entry['action_taken'] == 'MOVED to AI_ACTION_REQUIRED'
            assert entry['subject'] == 'Action Required Email'
            assert 'details' in entry  # Full classification stored in details
    
    def test_log_action_updates_existing_entry(self, app):
        """Test that log_action updates entry if msg_id already exists."""
        from utils.db_logger import log_action, get_log_entry
        
        with app.app_context():
            msg_id = 'test-update-entry'
            
            # First log
            log_action(
                msg_id=msg_id,
                classification={'category': 'REVIEW', 'action': 'ARCHIVE'},
                action_taken='ARCHIVED',
                subject='First Subject'
            )
            
            # Update log
            log_action(
                msg_id=msg_id,
                classification={'category': 'IMPORTANT', 'action': 'MOVE'},
                action_taken='MOVED to AI_IMPORTANT',
                subject='Updated Subject'
            )
            
            entry = get_log_entry(msg_id)
            
            # Should have updated values
            assert entry['ai_category'] == 'IMPORTANT'
            assert entry['action_taken'] == 'MOVED to AI_IMPORTANT'
            assert entry['subject'] == 'Updated Subject'
            
            # Should only have one entry in database
            count = ActionLog.query.filter_by(msg_id=msg_id).count()
            assert count == 1
    
    def test_log_action_handles_missing_classification_fields(self, app):
        """Test that log_action handles classification with missing fields."""
        from utils.db_logger import log_action, get_log_entry
        
        with app.app_context():
            # Minimal classification
            classification = {'category': 'REVIEW'}
            
            log_action(
                msg_id='test-minimal',
                classification=classification,
                action_taken='NO_ACTION',
                subject='Minimal Test Email'
            )
            
            entry = get_log_entry('test-minimal')
            
            assert entry is not None
            assert entry['ai_category'] == 'REVIEW'
            assert entry['action_taken'] == 'NO_ACTION'

