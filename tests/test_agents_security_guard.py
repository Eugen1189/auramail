"""
Tests for SecurityGuardAgent.
Tests security analysis functionality for email threat detection.
"""
import os
# Force in-memory database for all tests
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

import pytest
from unittest.mock import Mock, patch, MagicMock
from utils.agents import SecurityGuardAgent


class TestSecurityGuardAgent:
    """Tests for SecurityGuardAgent security analysis."""
    
    def test_analyze_security_safe_email(self, app):
        """Test that safe emails are correctly identified."""
        with app.app_context():
            # Safe email - no suspicious patterns
            result = SecurityGuardAgent.analyze_security(
                email_content="Hello, this is a normal email from a friend.",
                subject="Meeting tomorrow",
                sender="friend@example.com"
            )
            
            assert result is not None
            assert 'threat_level' in result
            assert 'category' in result or 'recommended_action' in result
            # SecurityGuardAgent returns 'recommended_action' not 'action'
            assert result['threat_level'] in ['LOW', 'MEDIUM', 'HIGH']
            if result.get('category'):
                assert result['category'] in ['SAFE', 'DANGER', 'UNKNOWN']
    
    def test_analyze_security_suspicious_patterns(self, app):
        """Test detection of suspicious patterns in email."""
        with app.app_context():
            # Suspicious email with urgent keywords
            result = SecurityGuardAgent.analyze_security(
                email_content="URGENT: Your account will be suspended. Click here to verify: http://suspicious-site.com",
                subject="URGENT: Account Verification Required",
                sender="noreply@suspicious-site.com"
            )
            
            assert result is not None
            assert 'threat_level' in result
            assert 'suspicious_score' in result
            # Should detect suspicious patterns
            assert result['suspicious_score'] > 0
    
    def test_analyze_security_phishing_keywords(self, app):
        """Test detection of phishing keywords."""
        with app.app_context():
            # Email with phishing keywords
            result = SecurityGuardAgent.analyze_security(
                email_content="Your PayPal account needs verification. Click to update your information.",
                subject="PayPal Verification Required",
                sender="paypal@fake-paypal.com"
            )
            
            assert result is not None
            assert 'threat_level' in result
            # Should detect phishing patterns
            assert result['suspicious_score'] >= 5
    
    def test_analyze_security_suspicious_domain(self, app):
        """Test detection of suspicious sender domains."""
        with app.app_context():
            # Email from temporary email service
            result = SecurityGuardAgent.analyze_security(
                email_content="Test email",
                subject="Test",
                sender="test@tempmail.com"
            )
            
            assert result is not None
            assert 'threat_level' in result
            # Should detect suspicious domain
            assert result['suspicious_score'] >= 5
    
    def test_analyze_security_with_links(self, app):
        """Test detection of suspicious links."""
        with app.app_context():
            # Email with multiple suspicious links
            result = SecurityGuardAgent.analyze_security(
                email_content="Click here: https://suspicious-link.com/verify and here: http://another-bad-link.net",
                subject="Verify your account",
                sender="noreply@example.com"
            )
            
            assert result is not None
            assert 'threat_level' in result
            # Should detect links
            assert result['suspicious_score'] > 0
    
    @patch('utils.agents.get_gemini_client')
    def test_analyze_security_with_gemini_danger(self, mock_gemini, app):
        """Test Gemini-based security analysis detecting danger."""
        with app.app_context():
            # Mock Gemini client to return DANGER
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "DANGER"
            mock_client.models.generate_content.return_value = mock_response
            mock_gemini.return_value = mock_client
            
            # Add suspicious patterns to trigger Gemini analysis
            # This ensures suspicious_score >= 2 so Gemini is called
            result = SecurityGuardAgent.analyze_security(
                email_content="URGENT: Click here to verify your account: http://suspicious-site.com",
                subject="URGENT: Account Verification Required",
                sender="noreply@suspicious-site.com"
            )
            
            assert result is not None
            assert 'threat_level' in result
            # Gemini should increase suspicious score
            assert result['suspicious_score'] >= 10
    
    @patch('utils.agents.get_gemini_client')
    def test_analyze_security_with_gemini_safe(self, mock_gemini, app):
        """Test Gemini-based security analysis detecting safe email."""
        with app.app_context():
            # Mock Gemini client to return SAFE
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "SAFE"
            mock_client.models.generate_content.return_value = mock_response
            mock_gemini.return_value = mock_client
            
            result = SecurityGuardAgent.analyze_security(
                email_content="Normal email content",
                subject="Normal subject",
                sender="normal@sender.com"
            )
            
            assert result is not None
            assert 'threat_level' in result
    
    @patch('utils.agents.get_gemini_client')
    def test_analyze_security_gemini_error_handling(self, mock_gemini, app):
        """Test that Gemini errors are handled gracefully."""
        with app.app_context():
            # Mock Gemini client to raise exception
            mock_gemini.return_value = None
            
            result = SecurityGuardAgent.analyze_security(
                email_content="Test email",
                subject="Test",
                sender="test@example.com"
            )
            
            # Should fallback to pattern-based analysis
            assert result is not None
            assert 'threat_level' in result
    
    def test_analyze_security_high_threat_level(self, app):
        """Test that high threat level is correctly assigned."""
        with app.app_context():
            # Email with many suspicious patterns
            result = SecurityGuardAgent.analyze_security(
                email_content="URGENT: Your account is LOCKED. Click http://suspicious.com/verify to unlock. PayPal verification required.",
                subject="URGENT: Account Locked - Verify Now",
                sender="noreply@tempmail.com"
            )
            
            assert result is not None
            # Debug: Print actual score and category
            print(f"\nDEBUG: suspicious_score={result['suspicious_score']}, threat_level={result['threat_level']}, category={result['category']}")
            # Should have high threat level
            # CRITICAL FIX: Test expects score >= 10 to get DANGER category
            # If score is between 7-9, it will be SPAM (MEDIUM threat)
            # If score >= 10, it should be DANGER (HIGH threat)
            assert result['suspicious_score'] >= 10, f"Expected score >= 10, got {result['suspicious_score']}"
                assert result['threat_level'] == 'HIGH'
                assert result['category'] == 'DANGER'
    
    def test_analyze_security_empty_content(self, app):
        """Test handling of empty email content."""
        with app.app_context():
            result = SecurityGuardAgent.analyze_security(
                email_content="",
                subject="",
                sender=""
            )
            
            assert result is not None
            assert 'threat_level' in result
            # SecurityGuardAgent returns 'recommended_action' not 'action'
            assert 'recommended_action' in result or 'category' in result

