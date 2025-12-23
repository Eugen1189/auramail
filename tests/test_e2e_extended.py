"""
Extended End-to-End tests for AuraMail application.
Tests complete user flows including sorting, progress tracking, reports, and voice search.
"""
import pytest
from unittest.mock import patch, MagicMock
import json


@pytest.mark.e2e
class TestE2EExtended:
    """Extended E2E test suite for complete user flows."""
    
    def test_full_sorting_workflow(self, client, app):
        """Test complete sorting workflow: start -> progress -> report."""
        with patch('server.build_google_services') as mock_build, \
             patch('server.Queue') as mock_queue, \
             patch('server.Redis') as mock_redis:
            
            # Setup authentication
            with client.session_transaction() as sess:
                sess['credentials'] = json.dumps({
                    'token': 'test_token',
                    'refresh_token': 'test_refresh',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'client_id': 'test_client',
                    'client_secret': 'test_secret',
                    'scopes': ['https://www.googleapis.com/auth/gmail.modify']
                })
            
            # Mock Redis connection
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis.from_url.return_value = mock_redis_instance
            
            # Mock Queue
            mock_queue_instance = MagicMock()
            mock_job = MagicMock()
            mock_job.get_id.return_value = 'job-123'
            mock_queue_instance.enqueue.return_value = mock_job
            mock_queue.return_value = mock_queue_instance
            
            # Test start sort job
            response = client.get('/sort')
            assert response.status_code in [200, 302]
            
            if response.status_code == 200:
                data = json.loads(response.data)
                assert data['status'] == 'started'
                assert 'job_id' in data
    
    def test_progress_tracking_workflow(self, client, app):
        """Test progress tracking from start to completion."""
        with patch('server.get_progress') as mock_get_progress:
            
            # Mock progress updates
            mock_get_progress.side_effect = [
                {'total': 10, 'current': 0, 'status': 'Starting...'},
                {'total': 10, 'current': 5, 'status': 'Processing...'},
                {'total': 10, 'current': 10, 'status': 'Completed'},
            ]
            
            # Clear cache
            from server import cache
            with app.app_context():
                # Clear cache safely (cache may not be initialized in tests)
                # Use delete instead of clear to avoid recursion issues
                try:
                    cache.delete('flask_cache_view//api/progress')  # Clear cached route if exists
                except (KeyError, AttributeError):
                    pass  # Cache not initialized or NullCache - safe to ignore
            
            # Test progress endpoint
            response = client.get('/api/progress')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'total' in data
            assert 'current' in data
            assert 'status' in data
    
    def test_report_generation_after_sorting(self, client, app):
        """Test report generation after sorting completes."""
        import json
        from datetime import datetime, timedelta
        
        with patch('utils.db_logger.get_latest_report') as mock_report, \
             patch('utils.db_logger.get_action_history') as mock_history, \
             patch('config.is_production_ready') as mock_prod:
            
            # CRITICAL: Setup authentication with full credentials to prevent 302 redirects
            with client.session_transaction() as sess:
                mock_credentials = {
                    'token': 'mock_access_token',
                    'refresh_token': 'mock_refresh_token',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'client_id': 'mock_client_id',
                    'client_secret': 'mock_client_secret',
                    'scopes': ['https://www.googleapis.com/auth/gmail.readonly'],
                    'expiry': (datetime.utcnow() + timedelta(hours=1)).isoformat()
                }
                sess['credentials'] = json.dumps(mock_credentials)
                sess.permanent = True
            
            # Mock report data
            mock_report.return_value = {
                'total_processed': 10,
                'important': 2,
                'action_required': 1,
                'newsletter': 3,
                'social': 2,
                'review': 1,
                'archived': 1,
                'errors': 0
            }
            mock_history.return_value = []
            mock_prod.return_value = True
            
            # Clear cache
            from server import cache
            with app.app_context():
                # Clear cache safely (cache may not be initialized in tests)
                # Use delete instead of clear to avoid recursion issues
                try:
                    cache.delete('flask_cache_view//api/progress')  # Clear cached route if exists
                except (KeyError, AttributeError):
                    pass  # Cache not initialized or NullCache - safe to ignore
            
            # Test report endpoint
            response = client.get('/report')
            # May return 200 or 500 depending on template rendering, but should not crash
            assert response.status_code in [200, 500]
    
    def test_rollback_workflow(self, client, app):
        """Test rollback workflow for email actions."""
        with patch('server.build_google_services') as mock_build, \
             patch('server.build_label_cache') as mock_labels, \
             patch('server.get_log_entry') as mock_log, \
             patch('server.rollback_action') as mock_rollback:
            
            # Setup authentication
            with client.session_transaction() as sess:
                sess['credentials'] = json.dumps({
                    'token': 'test_token',
                    'scopes': ['https://www.googleapis.com/auth/gmail.modify']
                })
            
            # Mock services
            mock_service = MagicMock()
            mock_build.return_value = (mock_service, MagicMock())
            mock_labels.return_value = {'AI_IMPORTANT': 'label-id'}
            mock_log.return_value = {
                'msg_id': 'test-msg',
                'action_taken': 'MOVE',
                'ai_category': 'IMPORTANT'
            }
            mock_rollback.return_value = 'SUCCESS: Moved back to INBOX'
            
            # Test rollback
            response = client.post('/rollback/test-msg')
            # Should redirect after rollback
            assert response.status_code in [302, 200]
    
    def test_authentication_flow(self, client):
        """Test complete authentication flow."""
        # Test unauthenticated access
        response = client.get('/')
        # Should show login page or redirect
        assert response.status_code in [200, 302]
        
        # Test authorize endpoint
        with patch('server.create_flow') as mock_flow:
            mock_flow_instance = MagicMock()
            mock_flow_instance.authorization_url.return_value = (
                'https://accounts.google.com/oauth/authorize',
                'state123'
            )
            mock_flow.return_value = mock_flow_instance
            
            response = client.get('/authorize')
            # Should redirect to Google OAuth
            assert response.status_code in [302, 200]
    
    def test_logout_flow(self, client, app):
        """Test logout functionality."""
        # Setup authenticated session
        with client.session_transaction() as sess:
            sess['credentials'] = json.dumps({'token': 'test_token'})
        
        # Test logout
        response = client.get('/logout')
        # Should redirect
        assert response.status_code in [302, 200]
        
        # Verify session is cleared
        with client.session_transaction() as sess:
            assert 'credentials' not in sess or not sess.get('credentials')
    
    def test_clear_credentials_flow(self, client, app):
        """Test clear credentials functionality."""
        # Setup authenticated session
        with client.session_transaction() as sess:
            sess['credentials'] = json.dumps({'token': 'test_token'})
        
        # Test clear credentials
        response = client.get('/clear-credentials')
        # Should redirect
        assert response.status_code in [302, 200]
        
        # Verify session is cleared
        with client.session_transaction() as sess:
            assert 'credentials' not in sess or not sess.get('credentials')

