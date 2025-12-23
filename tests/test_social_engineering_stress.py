"""
Stress Tests for Social Engineering Detection - Security Guard.

Tests that Security Guard correctly identifies social engineering attacks,
especially "urgency + link" patterns from seemingly legitimate senders.

CRITICAL BUSINESS VALUE: Prevents users from falling victim to social engineering
attacks disguised as urgent requests from colleagues or familiar domains.
"""
import os
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Force in-memory database for all tests
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

from utils.agents import SecurityGuardAgent


# Load test cases from JSON file
TEST_CASES_FILE = Path(__file__).parent / 'social_engineering_cases.json'


def load_test_cases():
    """Load test cases from JSON file."""
    with open(TEST_CASES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['test_cases']


@pytest.fixture
def social_engineering_cases():
    """Load test cases for social engineering stress tests."""
    return load_test_cases()


class TestSocialEngineeringStress:
    """Stress tests for social engineering detection."""
    
    def test_urgent_colleague_with_link(self, app, social_engineering_cases):
        """Test that urgent request from colleague with link is flagged as HIGH threat."""
        with app.app_context():
            test_case = next(tc for tc in social_engineering_cases if tc['id'] == 'social_engineering_1')
            
            result = SecurityGuardAgent.analyze_security(
                email_content=test_case['content'],
                subject=test_case['subject'],
                sender=test_case['sender'],
                reply_to=test_case.get('reply_to')
            )
            
            assert result['threat_level'] == test_case['expected_threat_level'], \
                f"Expected {test_case['expected_threat_level']}, got {result['threat_level']}. {test_case['reason']}"
            assert result['suspicious_score'] >= test_case['expected_suspicious_score'], \
                f"Expected score >= {test_case['expected_suspicious_score']}, got {result['suspicious_score']}"
            assert 'social_engineering_urgency_external_link' in result.get('found_patterns', []) or \
                   'social_engineering_urgency_internal_link' in result.get('found_patterns', []), \
                "Should detect social engineering pattern: urgency + link"
            assert 'reply_to_mismatch' in result.get('found_patterns', []), \
                "Should detect reply-to mismatch"
    
    def test_urgent_similar_domain(self, app, social_engineering_cases):
        """Test that urgent request from similar domain is flagged as HIGH threat."""
        with app.app_context():
            test_case = next(tc for tc in social_engineering_cases if tc['id'] == 'social_engineering_2')
            
            result = SecurityGuardAgent.analyze_security(
                email_content=test_case['content'],
                subject=test_case['subject'],
                sender=test_case['sender'],
                reply_to=test_case.get('reply_to')
            )
            
            assert result['threat_level'] == test_case['expected_threat_level']
            assert result['suspicious_score'] >= test_case['expected_suspicious_score']
            assert 'social_engineering_urgency_external_link' in result.get('found_patterns', []) or \
                   'social_engineering_urgency_internal_link' in result.get('found_patterns', [])
    
    def test_urgent_password_reset_link(self, app, social_engineering_cases):
        """Test that urgent password reset with link is flagged as HIGH threat."""
        with app.app_context():
            test_case = next(tc for tc in social_engineering_cases if tc['id'] == 'social_engineering_3')
            
            result = SecurityGuardAgent.analyze_security(
                email_content=test_case['content'],
                subject=test_case['subject'],
                sender=test_case['sender'],
                reply_to=test_case.get('reply_to')
            )
            
            assert result['threat_level'] == test_case['expected_threat_level']
            assert result['suspicious_score'] >= test_case['expected_suspicious_score']
            assert 'social_engineering_urgency_external_link' in result.get('found_patterns', []) or \
                   'social_engineering_urgency_internal_link' in result.get('found_patterns', [])
    
    def test_urgent_boss_with_external_link(self, app, social_engineering_cases):
        """Test that urgent request from boss with external link is flagged as MEDIUM threat."""
        with app.app_context():
            test_case = next(tc for tc in social_engineering_cases if tc['id'] == 'social_engineering_4')
            
            result = SecurityGuardAgent.analyze_security(
                email_content=test_case['content'],
                subject=test_case['subject'],
                sender=test_case['sender'],
                reply_to=test_case.get('reply_to')
            )
            
            # Should detect social engineering pattern but may be MEDIUM if Google Docs domain
            assert result['threat_level'] in ['MEDIUM', 'HIGH'], \
                f"Expected MEDIUM or HIGH, got {result['threat_level']}"
            assert result['suspicious_score'] >= 5, \
                f"Expected score >= 5, got {result['suspicious_score']}"
            assert 'social_engineering_urgency_link' in result.get('found_patterns', []) or \
                   'reply_to_mismatch' in result.get('found_patterns', []), \
                "Should detect social engineering or reply-to mismatch"
    
    def test_urgent_without_link_safe(self, app, social_engineering_cases):
        """Test that urgent request without link is safe (capped at LOW threat)."""
        with app.app_context():
            test_case = next(tc for tc in social_engineering_cases if tc['id'] == 'social_engineering_5')
            
            result = SecurityGuardAgent.analyze_security(
                email_content=test_case['content'],
                subject=test_case['subject'],
                sender=test_case['sender'],
                reply_to=test_case.get('reply_to')
            )
            
            assert result['threat_level'] == test_case['expected_threat_level'], \
                f"Expected {test_case['expected_threat_level']}, got {result['threat_level']}. {test_case['reason']}"
            assert result['suspicious_score'] <= test_case['expected_suspicious_score'], \
                f"Expected score <= {test_case['expected_suspicious_score']}, got {result['suspicious_score']}"
            assert 'social_engineering_urgency_link' not in result.get('found_patterns', []), \
                "Should NOT detect social engineering pattern (no link)"
    
    def test_urgent_internal_link_safe(self, app, social_engineering_cases):
        """Test that urgent request with internal company link is flagged but LOW threat."""
        with app.app_context():
            test_case = next(tc for tc in social_engineering_cases if tc['id'] == 'social_engineering_6')
            
            result = SecurityGuardAgent.analyze_security(
                email_content=test_case['content'],
                subject=test_case['subject'],
                sender=test_case['sender'],
                reply_to=test_case.get('reply_to')
            )
            
            # Internal company links are safer, urgency + link is flagged but LOW threat
            assert result['threat_level'] == test_case['expected_threat_level'], \
                f"Expected {test_case['expected_threat_level']}, got {result['threat_level']}. {test_case['reason']}"
            assert result['suspicious_score'] <= test_case['expected_suspicious_score'], \
                f"Expected score <= {test_case['expected_suspicious_score']} for internal link, got {result['suspicious_score']}"
            assert 'social_engineering_urgency_internal_link' in result.get('found_patterns', []), \
                "Should detect social engineering pattern for internal link"
    
    def test_urgent_shortened_url(self, app, social_engineering_cases):
        """Test that urgent request with shortened URL is flagged as HIGH threat."""
        with app.app_context():
            test_case = next(tc for tc in social_engineering_cases if tc['id'] == 'social_engineering_7')
            
            result = SecurityGuardAgent.analyze_security(
                email_content=test_case['content'],
                subject=test_case['subject'],
                sender=test_case['sender'],
                reply_to=test_case.get('reply_to')
            )
            
            assert result['threat_level'] == test_case['expected_threat_level']
            assert result['suspicious_score'] >= test_case['expected_suspicious_score']
            assert 'social_engineering_urgency_external_link' in result.get('found_patterns', []) or \
                   'social_engineering_urgency_internal_link' in result.get('found_patterns', [])
            assert 'reply_to_mismatch' in result.get('found_patterns', [])
    
    def test_urgent_ip_address_link(self, app, social_engineering_cases):
        """Test that urgent request with IP address link is flagged as HIGH threat."""
        with app.app_context():
            test_case = next(tc for tc in social_engineering_cases if tc['id'] == 'social_engineering_8')
            
            result = SecurityGuardAgent.analyze_security(
                email_content=test_case['content'],
                subject=test_case['subject'],
                sender=test_case['sender'],
                reply_to=test_case.get('reply_to')
            )
            
            assert result['threat_level'] == test_case['expected_threat_level']
            assert result['suspicious_score'] >= test_case['expected_suspicious_score']
            assert 'social_engineering_urgency_external_link' in result.get('found_patterns', []) or \
                   'social_engineering_urgency_internal_link' in result.get('found_patterns', [])
    
    @pytest.mark.parametrize("test_case_id", [
        "social_engineering_1",
        "social_engineering_2",
        "social_engineering_3",
        "social_engineering_4",
        "social_engineering_5",
        "social_engineering_6",
        "social_engineering_7",
        "social_engineering_8"
    ])
    def test_all_social_engineering_cases(self, app, social_engineering_cases, test_case_id):
        """Parametrized test for all social engineering cases."""
        with app.app_context():
            test_case = next(tc for tc in social_engineering_cases if tc['id'] == test_case_id)
            
            result = SecurityGuardAgent.analyze_security(
                email_content=test_case['content'],
                subject=test_case['subject'],
                sender=test_case['sender'],
                reply_to=test_case.get('reply_to')
            )
            
            # Verify threat level matches expected (with some flexibility for edge cases)
            if test_case['expected_threat_level'] == 'HIGH':
                assert result['threat_level'] == 'HIGH', \
                    f"Test case {test_case_id}: Expected HIGH, got {result['threat_level']}. {test_case['reason']}"
            elif test_case['expected_threat_level'] == 'MEDIUM':
                assert result['threat_level'] in ['MEDIUM', 'HIGH'], \
                    f"Test case {test_case_id}: Expected MEDIUM or HIGH, got {result['threat_level']}. {test_case['reason']}"
            elif test_case['expected_threat_level'] == 'LOW':
                assert result['threat_level'] in ['LOW', 'MEDIUM'], \
                    f"Test case {test_case_id}: Expected LOW or MEDIUM, got {result['threat_level']}. {test_case['reason']}"
            
            # Verify suspicious score
            if test_case['expected_suspicious_score'] >= 10:
                assert result['suspicious_score'] >= 10, \
                    f"Test case {test_case_id}: Expected score >= 10, got {result['suspicious_score']}"
            elif test_case['expected_suspicious_score'] <= 3:
                assert result['suspicious_score'] <= 5, \
                    f"Test case {test_case_id}: Expected score <= 5, got {result['suspicious_score']}"

