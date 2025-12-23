"""
Tests for agent-based architecture in utils/agents.py.
Focuses on SecurityGuardAgent for security analysis.
"""
import os
# Force in-memory database for all tests
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

import pytest
from unittest.mock import Mock, MagicMock, patch
from utils.agents import SecurityGuardAgent, LibrarianAgent


class TestSecurityGuardAgent:
    """Tests for SecurityGuardAgent - security analysis of emails."""
    
    def test_analyze_security_detects_phishing_patterns(self, app):
        """Test that SecurityGuardAgent detects phishing patterns."""
        with app.app_context():
            from database import db
            db.create_all()
            
            # Test with suspicious content
            email_content = "URGENT: Verify your account now! Click here: http://fake-bank.com/login"
            subject = "URGENT: Account Verification Required"
            sender = "noreply@fake-bank.com"
            
            result = SecurityGuardAgent.analyze_security(email_content, subject, sender)
            
            assert 'is_safe' in result
            assert 'threat_level' in result
            assert 'suspicious_score' in result
            assert 'found_patterns' in result
            assert result['suspicious_score'] > 0
    
    def test_analyze_security_detects_suspicious_domains(self, app):
        """Test that SecurityGuardAgent detects suspicious sender domains."""
        with app.app_context():
            from database import db
            db.create_all()
            
            # Test with suspicious domain
            email_content = "Test email"
            subject = "Test"
            sender = "test@tempmail.com"
            
            result = SecurityGuardAgent.analyze_security(email_content, subject, sender)
            
            assert 'is_safe' in result
            assert 'threat_level' in result
            # Suspicious domain should increase score
            assert result['suspicious_score'] >= 5
    
    def test_analyze_security_safe_email_passes(self, app):
        """Test that SecurityGuardAgent allows safe emails."""
        with app.app_context():
            from database import db
            db.create_all()
            
            # Test with safe email
            email_content = "Hello, this is a normal email from a friend."
            subject = "Greetings"
            sender = "friend@example.com"
            
            result = SecurityGuardAgent.analyze_security(email_content, subject, sender)
            
            assert 'is_safe' in result
            assert 'threat_level' in result
            # Safe email should have low or zero score
            assert result['suspicious_score'] < 5
    
    def test_analyze_security_empty_content(self, app):
        """Test that SecurityGuardAgent handles empty content."""
        with app.app_context():
            from database import db
            db.create_all()
            
            # Mock Gemini to avoid API calls in tests
            with patch('utils.agents.get_gemini_client', return_value=None):
                result = SecurityGuardAgent.analyze_security("", "", "")
                
                assert 'is_safe' in result
                assert 'threat_level' in result
                assert 'suspicious_score' in result
                # Without Gemini, empty content should have low score
                assert result['suspicious_score'] < 5
    
    def test_analyze_security_handles_errors_gracefully(self, app):
        """Test that SecurityGuardAgent handles errors gracefully."""
        with app.app_context():
            from database import db
            db.create_all()
            
            # Mock Gemini client to raise error
            with patch('utils.agents.get_gemini_client', side_effect=Exception("API error")):
                result = SecurityGuardAgent.analyze_security("test", "test", "test@example.com")
                
                # Should return safe result on error
                assert 'is_safe' in result
                assert 'threat_level' in result
    
    def test_analyze_security_returns_proper_structure(self, app):
        """Test that analyze_security returns proper analysis structure."""
        with app.app_context():
            from database import db
            db.create_all()
            
            result = SecurityGuardAgent.analyze_security(
                "Test email content",
                "Test Subject",
                "test@example.com"
            )
            
            assert 'is_safe' in result
            assert 'threat_level' in result
            assert 'suspicious_score' in result
            assert 'found_patterns' in result
            assert 'category' in result
            assert 'recommended_action' in result
            assert 'message' in result
            assert isinstance(result['found_patterns'], list)


class TestLibrarianAgent:
    """Tests for LibrarianAgent - dashboard state assessment."""
    
    def test_is_already_processed_returns_false_for_new_message(self, app):
        """Test that is_already_processed returns False for new messages."""
        with app.app_context():
            from database import db, ActionLog
            db.create_all()
            
            result = LibrarianAgent.is_already_processed('new-msg-123')
            
            assert result is False
    
    def test_is_already_processed_returns_true_for_processed_message(self, app):
        """Test that is_already_processed returns True for processed messages."""
        with app.app_context():
            from database import db, ActionLog
            db.create_all()
            
            # Create a processed message
            entry = ActionLog(
                msg_id='processed-msg-123',
                subject='Test',
                ai_category='IMPORTANT',
                action_taken='MOVE'
            )
            db.session.add(entry)
            db.session.commit()
            
            result = LibrarianAgent.is_already_processed('processed-msg-123')
            
            assert result is True
    
    def test_is_already_processed_handles_database_error(self, app):
        """Test that is_already_processed handles database errors gracefully."""
        with app.app_context():
            from database import db
            db.create_all()
            
            # Mock database error
            with patch('utils.agents.ActionLog.query') as mock_query:
                mock_query.filter_by.side_effect = Exception("Database error")
                
                result = LibrarianAgent.is_already_processed('test-msg')
                
                # Should return False on error (graceful degradation)
                assert result is False
    
    def test_check_dashboard_state_with_mock_service(self, app):
        """Test that check_dashboard_state works with mocked Gmail service."""
        with app.app_context():
            from database import db
            db.create_all()
            
            # Create mock Gmail service
            mock_service = MagicMock()
            mock_response = {
                'resultSizeEstimate': 5
            }
            mock_service.users().messages().list().execute.return_value = mock_response
            
            result = LibrarianAgent.check_dashboard_state(mock_service)
            
            assert 'status' in result
            assert 'message' in result
            assert 'inbox_count' in result
            assert 'processed_count' in result
            assert result['inbox_count'] == 5
    
    def test_check_dashboard_state_handles_service_error(self, app):
        """Test that check_dashboard_state handles Gmail service errors gracefully."""
        with app.app_context():
            from database import db
            db.create_all()
            
            # Create mock Gmail service that raises error
            mock_service = MagicMock()
            mock_service.users().messages().list().execute.side_effect = Exception("API error")
            
            result = LibrarianAgent.check_dashboard_state(mock_service)
            
            assert result['status'] == 'error'
            assert 'message' in result
            assert 'Помилка перевірки стану' in result['message']

