"""
Integration tests for database operations.
"""
import pytest
from datetime import datetime
from utils.db_logger import log_action, get_log_entry, get_action_history, save_report, get_latest_report
from database import ActionLog, Report, db


class TestDatabaseOperations:
    """Test suite for database operations."""
    
    def test_log_action_creates_entry(self, app):
        """Test that log_action creates a new database entry."""
        with app.app_context():
            classification = {
                'category': 'IMPORTANT',
                'description': 'Test description'
            }
            
            log_action(
                msg_id='test-msg-123',
                classification=classification,
                action_taken='MOVE',
                subject='Test Subject'
            )
            
            # Verify entry exists
            entry = ActionLog.query.filter_by(msg_id='test-msg-123').first()
            assert entry is not None
            assert entry.ai_category == 'IMPORTANT'
            assert entry.action_taken == 'MOVE'
            assert entry.subject == 'Test Subject'
    
    def test_log_action_updates_existing_entry(self, app):
        """Test that log_action updates existing entry if msg_id already exists."""
        with app.app_context():
            # Create initial entry
            initial_classification = {'category': 'REVIEW', 'description': 'Initial'}
            log_action('test-msg-456', initial_classification, 'ARCHIVE', 'Initial Subject')
            
            # Update with new classification
            updated_classification = {'category': 'IMPORTANT', 'description': 'Updated'}
            log_action('test-msg-456', updated_classification, 'MOVE', 'Updated Subject')
            
            # Verify only one entry exists with updated data
            entries = ActionLog.query.filter_by(msg_id='test-msg-456').all()
            assert len(entries) == 1
            assert entries[0].ai_category == 'IMPORTANT'
            assert entries[0].action_taken == 'MOVE'
    
    def test_get_log_entry_retrieves_correct_entry(self, app):
        """Test that get_log_entry retrieves the correct entry."""
        with app.app_context():
            classification = {'category': 'NEWSLETTER', 'description': 'Newsletter test'}
            log_action('test-msg-789', classification, 'DELETE', 'Newsletter Subject')
            
            entry = get_log_entry('test-msg-789')
            
            assert entry is not None
            # get_log_entry returns dict, not model object
            if isinstance(entry, dict):
                assert entry['msg_id'] == 'test-msg-789'
                assert entry['ai_category'] == 'NEWSLETTER'
            else:
                assert entry.msg_id == 'test-msg-789'
                assert entry.ai_category == 'NEWSLETTER'
    
    def test_save_report_creates_report(self, app):
        """Test that save_report creates a new report entry."""
        with app.app_context():
            stats = {
                'total_processed': 100,
                'important': 10,
                'action_required': 5,
                'newsletter': 20,
                'social': 15,
                'review': 30,
                'archived': 20,
                'errors': 0
            }
            
            save_report(stats)
            
            # Verify report exists
            report = Report.query.order_by(Report.created_at.desc()).first()
            assert report is not None
            assert report.total_processed == 100
            assert report.important == 10
            assert report.archived == 20
    
    def test_get_latest_report_retrieves_most_recent(self, app):
        """Test that get_latest_report retrieves the most recent report."""
        with app.app_context():
            # Create two reports
            save_report({'total_processed': 50, 'important': 5, 'action_required': 2, 
                        'newsletter': 10, 'social': 5, 'review': 15, 'archived': 10, 'errors': 2})
            
            import time
            time.sleep(0.1)  # Ensure different timestamps
            
            save_report({'total_processed': 100, 'important': 10, 'action_required': 5,
                        'newsletter': 20, 'social': 15, 'review': 30, 'archived': 20, 'errors': 0})
            
            latest = get_latest_report()
            
            assert latest is not None
            # get_latest_report returns dict, not model object
            if isinstance(latest, dict):
                assert latest['total_processed'] == 100
            else:
                assert latest.total_processed == 100

