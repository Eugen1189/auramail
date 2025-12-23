"""
E2E (End-to-End) tests for AuraMail web application.
Tests the full user flow from login to email sorting.

Note: These tests require a running Flask server.
Run with: pytest tests/test_e2e.py -v --e2e
"""
import pytest
import time
import json
from unittest.mock import patch, Mock

# CRITICAL FIX: Стратегія "Розділяй і володарюй"
# Маркування E2E тестів для правильного порядку виконання
pytestmark = pytest.mark.order(-1)  # E2E тести виконуються останніми


@pytest.mark.e2e
@pytest.mark.skipif(True, reason="E2E tests require running server - run manually")
class TestE2EFlow:
    """End-to-end tests for the complete user flow."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from server import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        with app.test_client() as client:
            with app.app_context():
                yield client
    
    def test_full_user_flow_login_to_dashboard(self, client):
        """Test complete flow: login -> dashboard -> sort -> report."""
        # Step 1: Access home page (should show login)
        response = client.get('/')
        assert response.status_code == 200
        assert 'login' in response.get_data(as_text=True).lower() or 'auramail' in response.get_data(as_text=True).lower()
        
        # Step 2: Authorize (mock OAuth flow)
        with patch('server.create_flow') as mock_flow:
            mock_flow_instance = Mock()
            mock_flow_instance.authorization_url.return_value = (
                'https://accounts.google.com/authorize?test=1',
                'test-state'
            )
            mock_flow.return_value = mock_flow_instance
            
            response = client.get('/authorize')
            assert response.status_code == 302
    
    def test_sorting_workflow(self, client):
        """Test sorting workflow with mocked credentials."""
        mock_credentials = json.dumps({
            'token': 'test-token',
            'refresh_token': 'test-refresh',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret',
            'scopes': ['https://www.googleapis.com/auth/gmail.readonly']
        })
        
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess['credentials'] = mock_credentials
        
        # Test start sort job
        with patch('server.Redis') as mock_redis_class, \
             patch('server.Queue') as mock_queue_class:
            
            mock_redis = Mock()
            mock_redis.ping.return_value = True
            mock_redis_class.from_url.return_value = mock_redis
            
            mock_queue = Mock()
            mock_job = Mock()
            mock_job.get_id.return_value = 'test-job-123'
            mock_queue.enqueue.return_value = mock_job
            mock_queue_class.return_value = mock_queue
            
            response = client.post('/sort')
            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert data['status'] == 'started'
        
        # Test progress API
        with patch('server.get_progress') as mock_progress:
            mock_progress.return_value = {
                'total': 10,
                'current': 5,
                'status': 'Processing',
                'details': 'Processing emails...'
            }
            
            response = client.get('/api/progress')
            assert response.status_code == 200
            data = json.loads(response.get_data())
            assert data['current'] == 5
            assert data['total'] == 10
        
        # Test report page
        with patch('server.get_latest_report') as mock_report, \
             patch('server.get_action_history') as mock_history, \
             patch('server.is_production_ready') as mock_prod:
            
            mock_report.return_value = {
                'total_processed': 10,
                'important': 2,
                'action_required': 1,
                'newsletter': 3,
                'social': 1,
                'review': 2,
                'archived': 1,
                'errors': 0
            }
            mock_history.return_value = []
            mock_prod.return_value = True
            
            response = client.get('/report')
            assert response.status_code == 200


@pytest.mark.integration
class TestIntegrationFlow:
    """Integration tests that test multiple components together."""
    
    # CRITICAL FIX: Remove local client fixture - use logged_in_client from conftest.py instead
    # This prevents conflicts and ensures proper session handling
    
    @patch('server.Redis')
    @patch('server.build_google_services')
    @patch('server.get_action_history')
    @patch('server.calculate_stats')
    @patch('server.get_daily_stats')
    @patch('server.get_followup_stats')
    @patch('server.get_user_credentials')
    def test_dashboard_data_integration(
        self, mock_get_credentials, mock_followup_stats, mock_daily_stats, mock_calculate_stats,
        mock_action_history, mock_build_services, mock_redis_class, logged_in_client
    ):
        """Test that dashboard integrates all data sources correctly."""
        from google.oauth2.credentials import Credentials
        import json
        from datetime import datetime, timedelta
        
        # Setup mocks
        mock_creds = Mock(spec=Credentials)
        mock_get_credentials.return_value = mock_creds
        
        # CRITICAL FIX: Встановлюємо credentials у session перед запитом
        # Це гарантує, що credentials є в session навіть коли виникають помилки
        mock_credentials = {
            'token': 'mock_access_token',
            'refresh_token': 'mock_refresh_token',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'mock_client_id',
            'client_secret': 'mock_client_secret',
            'scopes': ['https://www.googleapis.com/auth/gmail.modify'],
            'expiry': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        
        # CRITICAL FIX: Встановлюємо credentials у session перед запитом
        with logged_in_client.session_transaction() as sess:
            sess['credentials'] = json.dumps(mock_credentials)
            sess.permanent = True
        
        mock_service = Mock()
        mock_profile = Mock()
        mock_profile.execute.return_value = {
            'emailAddress': 'test@example.com'
        }
        mock_users = Mock()
        mock_users.getProfile.return_value = mock_profile
        mock_service.users.return_value = mock_users
        mock_build_services.return_value = (mock_service, None)
        
        # Ensure get_action_history returns a list of dicts matching ActionLog.to_dict() format
        # This matches what get_action_history() actually returns (via entry.to_dict())
        mock_action_history.return_value = [
            {
                'msg_id': '1',
                'message_id': '1',
                'subject': 'Test Email 1',
                'original_subject': 'Test Email 1',
                'ai_category': 'IMPORTANT',
                'action_taken': 'MOVED to AI_IMPORTANT',
                'is_followup_pending': False,
                'expected_reply_date': None,
                'followup_sent': False,
                'reason': 'Test reason',
                'ai_description': 'Test reason',
                'timestamp': '2025-12-15T10:00:00',
                'details': {}
            }
        ]
        mock_calculate_stats.return_value = {
            'total_processed': 1,
            'important': 1,
            'action_required': 0,
            'newsletter': 0,
            'social': 0,
            'review': 0,
            'archived': 0,
            'errors': 0
        }
        mock_daily_stats.return_value = {'2025-12-12': 1}
        mock_followup_stats.return_value = {'pending': 0, 'overdue': 0}
        
        # Mock Redis to prevent connection attempts
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.from_url.return_value = mock_redis_instance
        
        # CRITICAL FIX: logged_in_client fixture already sets credentials in session
        # No need to set them again - just use logged_in_client directly
        
        # Clear cache before test to ensure function executes
        from flask import current_app
        with logged_in_client.application.app_context():
            cache = current_app.extensions.get('cache')
            if cache:
                cache.clear()
        
        # CRITICAL FIX: Use logged_in_client instead of client for proper session handling
        # Test dashboard
        response = logged_in_client.get('/')
        
        # Debug: print response if error
        if response.status_code != 200:
            response_text = response.get_data(as_text=True)
            print(f"\n=== DEBUG: Response status: {response.status_code} ===")
            print(f"Response data (first 1000 chars): {response_text[:1000]}")
            print("=== END DEBUG ===\n")
            # Re-raise to see full traceback
            raise AssertionError(f"Expected 200, got {response.status_code}. Response: {response_text[:500]}")
        
        assert response.status_code == 200
        
        # Verify all functions were called
        mock_get_credentials.assert_called_once()
        mock_build_services.assert_called_once()
        mock_action_history.assert_called_once()
        mock_calculate_stats.assert_called_once()
        mock_daily_stats.assert_called_once()
        mock_followup_stats.assert_called_once()

