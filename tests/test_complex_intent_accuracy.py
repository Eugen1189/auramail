"""
Tests for Complex Intent Accuracy - Analyst Agent.

Tests that Analyst Agent correctly identifies hidden actions in emails
that appear to be newsletters or marketing content but contain action requests.

CRITICAL BUSINESS VALUE: Ensures AI doesn't miss important action items
hidden in seemingly non-urgent emails.
"""
import os
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Force in-memory database for all tests
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

from utils.gemini_processor import classify_email_with_gemini, get_gemini_client


# Load test cases from JSON file
TEST_CASES_FILE = Path(__file__).parent / 'complex_intent_cases.json'


def load_test_cases():
    """Load test cases from JSON file."""
    with open(TEST_CASES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['test_cases']


@pytest.fixture
def test_cases():
    """Load test cases for complex intent accuracy."""
    return load_test_cases()


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    return mock_client, mock_response


class TestComplexIntentAccuracy:
    """Tests for complex intent detection accuracy."""
    
    def test_hidden_action_in_newsletter(self, app, test_cases, mock_gemini_client):
        """Test that newsletter with hidden action is classified as ACTION_REQUIRED."""
        with app.app_context():
            mock_client, mock_response = mock_gemini_client
            
            # Find test case with hidden action
            test_case = next(tc for tc in test_cases if tc['id'] == 'hidden_action_1')
            
            # Mock Gemini response to return ACTION_REQUIRED
            mock_response.text = json.dumps({
                'category': 'ACTION_REQUIRED',
                'label_name': 'AI_ACTION_REQUIRED',
                'action': 'MOVE',
                'urgency': 'MEDIUM',
                'description': 'Contains action request: Підтвердьте вашу присутність до завтра',
                'extracted_entities': {}
            })
            
            with patch('utils.gemini_processor.get_gemini_client', return_value=mock_client):
                result = classify_email_with_gemini(
                    mock_client,
                    f"Subject: {test_case['subject']}\n\n{test_case['content']}"
                )
            
            assert result['category'] == test_case['expected_category'], \
                f"Expected {test_case['expected_category']}, got {result['category']}. Reason: {test_case['reason']}"
            assert result['action'] == test_case['expected_action'], \
                f"Expected action {test_case['expected_action']}, got {result['action']}"
            assert result['urgency'] == test_case['expected_urgency'], \
                f"Expected urgency {test_case['expected_urgency']}, got {result['urgency']}"
    
    def test_marketing_with_deadline(self, app, test_cases, mock_gemini_client):
        """Test that marketing email with deadline is classified correctly."""
        with app.app_context():
            mock_client, mock_response = mock_gemini_client
            
            test_case = next(tc for tc in test_cases if tc['id'] == 'hidden_action_2')
            
            mock_response.text = json.dumps({
                'category': 'ACTION_REQUIRED',
                'label_name': 'AI_ACTION_REQUIRED',
                'action': 'MOVE',
                'urgency': 'HIGH',
                'description': 'Contains deadline: до 15 січня',
                'extracted_entities': {
                    'due_date': '2025-01-15'
                }
            })
            
            with patch('utils.gemini_processor.get_gemini_client', return_value=mock_client):
                result = classify_email_with_gemini(
                    mock_client,
                    f"Subject: {test_case['subject']}\n\n{test_case['content']}"
                )
            
            assert result['category'] == test_case['expected_category']
            assert result['action'] == test_case['expected_action']
            assert result['urgency'] == test_case['expected_urgency']
    
    def test_pure_newsletter_stays_newsletter(self, app, test_cases, mock_gemini_client):
        """Test that pure newsletter without action stays as NEWSLETTER."""
        with app.app_context():
            mock_client, mock_response = mock_gemini_client
            
            test_case = next(tc for tc in test_cases if tc['id'] == 'hidden_action_3')
            
            mock_response.text = json.dumps({
                'category': 'NEWSLETTER',
                'label_name': 'AI_NEWSLETTER',
                'action': 'ARCHIVE',
                'urgency': 'LOW',
                'description': 'Pure newsletter content without action requests',
                'extracted_entities': {}
            })
            
            with patch('utils.gemini_processor.get_gemini_client', return_value=mock_client):
                result = classify_email_with_gemini(
                    mock_client,
                    f"Subject: {test_case['subject']}\n\n{test_case['content']}"
                )
            
            assert result['category'] == test_case['expected_category']
            assert result['action'] == test_case['expected_action']
            assert result['urgency'] == test_case['expected_urgency']
    
    def test_social_notification_with_action(self, app, test_cases, mock_gemini_client):
        """Test that social notification with action request is ACTION_REQUIRED."""
        with app.app_context():
            mock_client, mock_response = mock_gemini_client
            
            test_case = next(tc for tc in test_cases if tc['id'] == 'hidden_action_4')
            
            mock_response.text = json.dumps({
                'category': 'ACTION_REQUIRED',
                'label_name': 'AI_ACTION_REQUIRED',
                'action': 'MOVE',
                'urgency': 'MEDIUM',
                'description': 'Contains action request: підтвердіть ваш профіль',
                'extracted_entities': {}
            })
            
            with patch('utils.gemini_processor.get_gemini_client', return_value=mock_client):
                result = classify_email_with_gemini(
                    mock_client,
                    f"Subject: {test_case['subject']}\n\n{test_case['content']}"
                )
            
            assert result['category'] == test_case['expected_category']
            assert result['action'] == test_case['expected_action']
    
    def test_bill_disguised_as_newsletter(self, app, test_cases, mock_gemini_client):
        """Test that bill notification disguised as newsletter is ACTION_REQUIRED."""
        with app.app_context():
            mock_client, mock_response = mock_gemini_client
            
            test_case = next(tc for tc in test_cases if tc['id'] == 'hidden_action_5')
            
            mock_response.text = json.dumps({
                'category': 'ACTION_REQUIRED',
                'label_name': 'AI_BILLS',
                'action': 'MOVE',
                'urgency': 'HIGH',
                'description': 'Contains payment deadline: до 20 січня',
                'extracted_entities': {
                    'due_date': '2025-01-20',
                    'amount': '1500 UAH'
                }
            })
            
            with patch('utils.gemini_processor.get_gemini_client', return_value=mock_client):
                result = classify_email_with_gemini(
                    mock_client,
                    f"Subject: {test_case['subject']}\n\n{test_case['content']}"
                )
            
            assert result['category'] == test_case['expected_category']
            assert result['action'] == test_case['expected_action']
            assert result['urgency'] == test_case['expected_urgency']
            
            # Verify extracted entities
            entities = result.get('extracted_entities', {})
            assert entities.get('due_date') == '2025-01-20'
            assert entities.get('amount') == '1500 UAH'
    
    def test_rsvp_request_in_newsletter(self, app, test_cases, mock_gemini_client):
        """Test that RSVP request in newsletter is ACTION_REQUIRED."""
        with app.app_context():
            mock_client, mock_response = mock_gemini_client
            
            test_case = next(tc for tc in test_cases if tc['id'] == 'hidden_action_6')
            
            mock_response.text = json.dumps({
                'category': 'ACTION_REQUIRED',
                'label_name': 'AI_EVENTS',
                'action': 'MOVE',
                'urgency': 'MEDIUM',
                'description': 'Contains RSVP request: підтвердіть вашу присутність',
                'extracted_entities': {
                    'due_date': '2025-01-20'
                }
            })
            
            with patch('utils.gemini_processor.get_gemini_client', return_value=mock_client):
                result = classify_email_with_gemini(
                    mock_client,
                    f"Subject: {test_case['subject']}\n\n{test_case['content']}"
                )
            
            assert result['category'] == test_case['expected_category']
            assert result['action'] == test_case['expected_action']
    
    def test_survey_request_in_newsletter(self, app, test_cases, mock_gemini_client):
        """Test that survey request in newsletter is ACTION_REQUIRED."""
        with app.app_context():
            mock_client, mock_response = mock_gemini_client
            
            test_case = next(tc for tc in test_cases if tc['id'] == 'hidden_action_8')
            
            mock_response.text = json.dumps({
                'category': 'ACTION_REQUIRED',
                'label_name': 'AI_FEEDBACK',
                'action': 'MOVE',
                'urgency': 'LOW',
                'description': 'Contains survey request with deadline',
                'extracted_entities': {}
            })
            
            with patch('utils.gemini_processor.get_gemini_client', return_value=mock_client):
                result = classify_email_with_gemini(
                    mock_client,
                    f"Subject: {test_case['subject']}\n\n{test_case['content']}"
                )
            
            assert result['category'] == test_case['expected_category']
            assert result['action'] == test_case['expected_action']
    
    @pytest.mark.parametrize("test_case_id", [
        "hidden_action_1",
        "hidden_action_2",
        "hidden_action_3",
        "hidden_action_4",
        "hidden_action_5",
        "hidden_action_6",
        "hidden_action_7",
        "hidden_action_8"
    ])
    def test_all_complex_intent_cases(self, app, test_cases, mock_gemini_client, test_case_id):
        """Parametrized test for all complex intent cases."""
        with app.app_context():
            mock_client, mock_response = mock_gemini_client
            
            test_case = next(tc for tc in test_cases if tc['id'] == test_case_id)
            
            # Create mock response based on expected category
            mock_response.text = json.dumps({
                'category': test_case['expected_category'],
                'label_name': f"AI_{test_case['expected_category']}",
                'action': test_case['expected_action'],
                'urgency': test_case['expected_urgency'],
                'description': test_case['reason'],
                'extracted_entities': {}
            })
            
            with patch('utils.gemini_processor.get_gemini_client', return_value=mock_client):
                result = classify_email_with_gemini(
                    mock_client,
                    f"Subject: {test_case['subject']}\n\n{test_case['content']}"
                )
            
            assert result['category'] == test_case['expected_category'], \
                f"Test case {test_case_id}: Expected {test_case['expected_category']}, got {result['category']}. {test_case['reason']}"
            assert result['action'] == test_case['expected_action'], \
                f"Test case {test_case_id}: Expected action {test_case['expected_action']}, got {result['action']}"
            assert result['urgency'] == test_case['expected_urgency'], \
                f"Test case {test_case_id}: Expected urgency {test_case['expected_urgency']}, got {result['urgency']}"



