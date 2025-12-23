"""
Extended tests for db_logger module.
Tests core functionality with in-memory database.
"""
import os
# Force in-memory database for all tests - prevent any file-based database usage
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

import pytest
from datetime import datetime, date
from utils.db_logger import log_action, save_report, get_latest_report
from database import ActionLog, Report, db

# CRITICAL FIX: Стратегія "Розділяй і володарюй"
# Маркування тестів БД для правильного порядку виконання
pytestmark = pytest.mark.order(1)  # Тести БД виконуються першими


def setup_test_session():
    """Helper to setup clean test session. Must be called within app context."""
    # Don't call db.session.remove() here - let db_session fixture handle it
    # Just ensure tables exist
    try:
        db.create_all()
        db.session.commit()
    except Exception:
        db.session.rollback()


def teardown_test_session():
    """Helper to cleanup test session. Must be called within app context."""
    # Don't call db.session.remove() here - let db_session fixture handle it
    # Just commit or rollback current transaction
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


class TestLogActionExtended:
    """Extended tests for log_action function."""
    
    def test_log_action_creates_new_entry(self, app, db_session):
        """Test that log_action creates a new database entry."""
        setup_test_session()
        
        classification = {
            'category': 'IMPORTANT',
            'description': 'Test description',
            'urgency': 'HIGH'
        }
        
        log_action(
            msg_id='test-msg-001',
            classification=classification,
            action_taken='MOVE',
            subject='Test Subject 1'
        )
        
        # Verify entry exists
        entry = ActionLog.query.filter_by(msg_id='test-msg-001').first()
        assert entry is not None
        assert entry.ai_category == 'IMPORTANT'
        assert entry.action_taken == 'MOVE'
        assert entry.subject == 'Test Subject 1'
    
    def test_log_action_updates_existing_entry(self, app, db_session):
        """Test that log_action updates existing entry if msg_id already exists."""
        setup_test_session()
        
        # Create initial entry
        initial_classification = {
            'category': 'REVIEW',
            'description': 'Initial description'
        }
        log_action(
            msg_id='test-msg-002',
            classification=initial_classification,
            action_taken='ARCHIVE',
            subject='Initial Subject'
        )
        
        # Update with new classification
        updated_classification = {
            'category': 'IMPORTANT',
            'description': 'Updated description'
        }
        log_action(
            msg_id='test-msg-002',
            classification=updated_classification,
            action_taken='MOVE',
            subject='Updated Subject'
        )
        
        # Verify only one entry exists with updated data
        entries = ActionLog.query.filter_by(msg_id='test-msg-002').all()
        assert len(entries) == 1
        assert entries[0].ai_category == 'IMPORTANT'
        assert entries[0].action_taken == 'MOVE'
        assert entries[0].subject == 'Updated Subject'
    
    def test_log_action_with_different_categories(self, app, db_session):
        """Test log_action with various email categories."""
        setup_test_session()
        
        categories = [
                'IMPORTANT',
                'ACTION_REQUIRED',
                'BILLS_INVOICES',
                'PERSONAL',
                'PROJECT',
                'REVIEW',
                'NEWSLETTER',
                'SOCIAL',
                'SPAM',
                'MARKETING'
            ]
            
        # Log all actions first
        # Each log_action already commits, so we don't need another commit
        # Clear session between operations to ensure clean transaction state
        import time
        for i, category in enumerate(categories):
            log_action(
                msg_id=f'test-category-{i}',
                classification={'category': category, 'description': f'{category} email'},
                action_taken='ARCHIVE',
                subject=f'{category} Subject'
            )
            # Small delay to ensure transaction is fully committed
            if i < len(categories) - 1:  # Don't delay after last operation
                time.sleep(0.01)  # 10ms delay between operations
                
        # Refresh session to ensure all entries are visible
        try:
            db.session.expire_all()
            # Commit any pending changes
            db.session.commit()
        except Exception:
            pass
                
        # Then verify all entries in a single query
        for i, category in enumerate(categories):
            entry = ActionLog.query.filter_by(msg_id=f'test-category-{i}').first()
            assert entry is not None, f"Entry for category {category} (index {i}) not found"
            assert entry.ai_category == category, f"Expected {category}, got {entry.ai_category}"
    
    def test_log_action_with_different_actions(self, app, db_session):
        """Test log_action with various action types."""
        setup_test_session()
        
        actions = ['MOVE', 'ARCHIVE', 'DELETE', 'LABEL']
        
        for i, action in enumerate(actions):
            log_action(
                msg_id=f'test-action-{i}',
                classification={'category': 'IMPORTANT', 'description': 'Test'},
                action_taken=action,
                subject=f'Test {action}'
            )
            
            entry = ActionLog.query.filter_by(msg_id=f'test-action-{i}').first()
            assert entry is not None
            assert entry.action_taken == action
    
    def test_log_action_with_expected_reply_date(self, app, db_session):
        """Test log_action with expected_reply_date in classification."""
        setup_test_session()
        
        classification = {
            'category': 'ACTION_REQUIRED',
            'description': 'Needs reply',
            'expected_reply_date': '2025-12-31',
            'expects_reply': True
        }
        
        log_action(
            msg_id='test-reply-date',
            classification=classification,
            action_taken='MOVE',
            subject='Action Required'
        )
        
        entry = ActionLog.query.filter_by(msg_id='test-reply-date').first()
        assert entry is not None
        # Use is_followup_pending instead of expects_reply (field name in ActionLog model)
        assert entry.is_followup_pending is True
        # expected_reply_date should be parsed to date object
        if entry.expected_reply_date:
            assert isinstance(entry.expected_reply_date, date)


class TestSaveReportExtended:
    """Extended tests for save_report function."""
    
    def test_save_report_creates_new_report(self, app):
        """Test that save_report creates a new report entry."""
        setup_test_session()
        
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
        assert report.action_required == 5
        assert report.newsletter == 20
        assert report.social == 15
        assert report.review == 30
        assert report.archived == 20
        assert report.errors == 0
    
    def test_save_report_multiple_reports(self, app):
        """Test saving multiple reports and ordering."""
        setup_test_session()
        
        # Create first report
        save_report({
                    'total_processed': 50,
                    'important': 5,
                    'action_required': 2,
                    'newsletter': 10,
                    'social': 5,
                    'review': 15,
                    'archived': 10,
                    'errors': 2
                })
                
            # Create second report
        save_report({
                    'total_processed': 100,
                    'important': 10,
                    'action_required': 5,
                    'newsletter': 20,
                    'social': 15,
                    'review': 30,
                    'archived': 20,
                    'errors': 0
                })
                
            # Verify both reports exist
        reports = Report.query.order_by(Report.created_at.desc()).all()
        assert len(reports) >= 2
                
            # Latest report should have higher total_processed
        latest = reports[0]
        assert latest.total_processed == 100
    
    def test_save_report_with_zero_values(self, app):
        """Test save_report with all zero values."""
        setup_test_session()
        
        stats = {
                'total_processed': 0,
                'important': 0,
                'action_required': 0,
                'newsletter': 0,
                'social': 0,
                'review': 0,
                'archived': 0,
                'errors': 0
            }
            
        save_report(stats)
                
        report = Report.query.order_by(Report.created_at.desc()).first()
        assert report is not None
        assert report.total_processed == 0
        assert report.errors == 0


class TestGetLatestReportExtended:
    """Extended tests for get_latest_report function."""
    
    def test_get_latest_report_retrieves_most_recent(self, app):
        """Test that get_latest_report retrieves the most recent report."""
        setup_test_session()
        
        # Create first report
        save_report({
                    'total_processed': 50,
                    'important': 5,
                    'action_required': 2,
                    'newsletter': 10,
                    'social': 5,
                    'review': 15,
                    'archived': 10,
                    'errors': 2
                })
                
            # Create second report
        save_report({
                    'total_processed': 100,
                    'important': 10,
                    'action_required': 5,
                    'newsletter': 20,
                    'social': 15,
                    'review': 30,
                    'archived': 20,
                    'errors': 0
                })
                
        latest = get_latest_report()
                
        assert latest is not None
            # get_latest_report returns dict, not model object
        if isinstance(latest, dict):
            assert latest['total_processed'] == 100
            assert latest['important'] == 10
        else:
            assert latest.total_processed == 100
            assert latest.important == 10
    
    def test_get_latest_report_returns_default_when_no_reports(self, app):
        """Test that get_latest_report returns default dict when no reports exist."""
        setup_test_session()
        
        latest = get_latest_report()
            
        # Should return default dict with zeros when no reports exist
        assert latest is not None
        assert isinstance(latest, dict)
        assert latest['total_processed'] == 0
        assert latest['archived'] == 0
        assert 'errors' in latest


class TestDatabaseIntegration:
    """Integration tests for db_logger with database."""
    
    def test_log_action_and_query_together(self, app, db_session):
        """Test that logged actions can be queried from database."""
        setup_test_session()
        
        # Log multiple actions
        import time
        for i in range(5):
            log_action(
                msg_id=f'integration-test-{i}',
                classification={'category': 'IMPORTANT', 'description': f'Test {i}'},
                action_taken='MOVE',
                subject=f'Integration Test {i}'
            )
            # Small delay between operations to prevent locking
            if i < 4:  # Don't delay after last operation
                time.sleep(0.01)  # Small delay between operations
                
        # Refresh session to ensure all entries are visible
        try:
            db.session.expire_all()
            # Commit any pending changes
            db.session.commit()
        except Exception:
            pass
                
        # Query all entries
        entries = ActionLog.query.all()
        assert len(entries) == 5
                
            # Verify each entry
        for i in range(5):
            entry = ActionLog.query.filter_by(msg_id=f'integration-test-{i}').first()
            assert entry is not None
            assert entry.ai_category == 'IMPORTANT'
            assert entry.action_taken == 'MOVE'
    
    def test_save_report_and_get_latest_together(self, app):
        """Test saving report and retrieving it."""
        setup_test_session()
        
        # Save report
        stats = {
                    'total_processed': 200,
                    'important': 20,
                    'action_required': 10,
                    'newsletter': 40,
                    'social': 30,
                    'review': 60,
                    'archived': 40,
                    'errors': 0
                }
        save_report(stats)
                
            # Get latest report
        latest = get_latest_report()
        assert latest is not None
                
        if isinstance(latest, dict):
            assert latest['total_processed'] == 200
        else:
            assert latest.total_processed == 200
