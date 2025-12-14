"""
Unit and Integration tests for Voice Search functionality.
Tests transform_to_gmail_query, voice_search_task, and /voice/search endpoint.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, Mock


class TestTransformToGmailQuery:
    """Unit tests for transform_to_gmail_query function."""
    
    @patch('utils.gemini_processor._call_gemini_api')
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.get_gemini_client')
    def test_transform_to_gmail_query_success(self, mock_get_client, mock_rate_limit, mock_call_api):
        """Test successful transformation of natural language to Gmail query."""
        from utils.gemini_processor import transform_to_gmail_query
        
        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_rate_limit.return_value = True  # Rate limit OK
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.text = "from:ivan after:2025/12/11"
        mock_call_api.return_value = mock_response
        
        # Test
        result = transform_to_gmail_query("знайди листи від Івана за вчора")
        
        # Verify
        assert result == "from:ivan after:2025/12/11"
        mock_rate_limit.assert_called_once()
        mock_call_api.assert_called_once()
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.get_gemini_client')
    def test_transform_to_gmail_query_empty_input(self, mock_get_client, mock_rate_limit):
        """Test transformation with empty input."""
        from utils.gemini_processor import transform_to_gmail_query
        
        result = transform_to_gmail_query("")
        assert result == ""
        
        result = transform_to_gmail_query(None)
        assert result == ""
    
    @patch('utils.gemini_processor.get_gemini_client')
    def test_transform_to_gmail_query_no_client(self, mock_get_client):
        """Test transformation when Gemini client is not available."""
        from utils.gemini_processor import transform_to_gmail_query
        
        mock_get_client.return_value = None
        
        result = transform_to_gmail_query("знайди листи")
        assert result == ""
    
    @patch('utils.gemini_processor._call_gemini_api')
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.get_gemini_client')
    @patch('utils.gemini_processor.time.sleep')  # Mock time.sleep in the module to avoid actual waiting
    def test_transform_to_gmail_query_rate_limit_timeout(self, mock_sleep, mock_get_client, mock_rate_limit, mock_call_api):
        """Test transformation when rate limit timeout is reached."""
        from utils.gemini_processor import transform_to_gmail_query
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        # Rate limit always returns False (blocked)
        mock_rate_limit.return_value = False
        # Mock sleep to avoid actual waiting (returns immediately)
        mock_sleep.return_value = None
        
        result = transform_to_gmail_query("знайди листи")
        
        # Should return empty string after timeout (max_wait_iterations = 120)
        assert result == ""
        # Rate limit should be called multiple times (up to max_wait_iterations = 120)
        assert mock_rate_limit.call_count >= 120, \
            f"Expected at least 120 rate limit checks, got {mock_rate_limit.call_count}"
        # Sleep should be called (120-1) times (one less than iterations, since we break on the last one)
        # Actually, it should be called 120 times (once per iteration before checking again)
        assert mock_sleep.call_count >= 119, \
            f"Expected at least 119 sleep calls, got {mock_sleep.call_count}"
    
    @patch('utils.gemini_processor._call_gemini_api')
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.get_gemini_client')
    def test_transform_to_gmail_query_strips_markdown(self, mock_get_client, mock_rate_limit, mock_call_api):
        """Test that markdown code blocks are stripped from response."""
        from utils.gemini_processor import transform_to_gmail_query
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_rate_limit.return_value = True
        
        # Mock response with markdown
        mock_response = MagicMock()
        mock_response.text = "```from:test@example.com```"
        mock_call_api.return_value = mock_response
        
        result = transform_to_gmail_query("знайди листи")
        
        assert result == "from:test@example.com"
        assert "```" not in result
    
    @patch('utils.gemini_processor._call_gemini_api')
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.get_gemini_client')
    def test_transform_to_gmail_query_handles_api_error(self, mock_get_client, mock_rate_limit, mock_call_api):
        """Test transformation handles API errors gracefully."""
        from utils.gemini_processor import transform_to_gmail_query
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_rate_limit.return_value = True
        mock_call_api.side_effect = Exception("API Error")
        
        result = transform_to_gmail_query("знайди листи")
        
        assert result == ""
    
    @patch('utils.gemini_processor._call_gemini_api')
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.get_gemini_client')
    def test_transform_to_gmail_query_long_response(self, mock_get_client, mock_rate_limit, mock_call_api):
        """Test transformation filters out overly long responses."""
        from utils.gemini_processor import transform_to_gmail_query
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_rate_limit.return_value = True
        
        # Mock response that's too long (> 500 chars)
        mock_response = MagicMock()
        mock_response.text = "a" * 600
        mock_call_api.return_value = mock_response
        
        result = transform_to_gmail_query("знайди листи")
        
        # Should return empty string for overly long response
        assert result == ""


class TestVoiceSearchTask:
    """Unit tests for voice_search_task function."""
    
    @patch('utils.gmail_api.find_emails_by_query')
    @patch('tasks.build_google_services')
    @patch('tasks.get_message_content')
    @patch('utils.gemini_processor.transform_to_gmail_query')
    @patch('tasks.create_app_for_worker')
    def test_voice_search_task_success(self, mock_create_app, mock_transform,
                                        mock_get_content, mock_build_services,
                                        mock_find_emails, app):
        """Test successful voice search task execution."""
        from tasks import voice_search_task
        
        mock_create_app.return_value = app
        mock_transform.return_value = "from:test@example.com"
        
        mock_service = MagicMock()
        mock_build_services.return_value = (mock_service, MagicMock())
        
        # Mock search results
        mock_find_emails.return_value = [
            {'id': 'msg1', 'threadId': 'thread1'},
            {'id': 'msg2', 'threadId': 'thread2'}
        ]
        
        # Mock message content
        mock_get_content.side_effect = [
            ('Email content 1', 'Subject 1'),
            ('Email content 2', 'Subject 2')
        ]
        
        credentials_json = json.dumps({
            'token': 'test_token',
            'refresh_token': 'test_refresh',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test_client',
            'client_secret': 'test_secret',
            'scopes': ['https://www.googleapis.com/auth/gmail.modify']
        })
        
        with app.app_context():
            result = voice_search_task(credentials_json, "знайди листи від теста")
        
        assert result['status'] == 'success'
        assert result['query'] == "знайди листи від теста"
        assert result['gmail_query'] == "from:test@example.com"
        assert result['total_found'] == 2
        assert len(result['results']) == 2
        assert result['results'][0]['subject'] == 'Subject 1'
    
    @patch('utils.gemini_processor.transform_to_gmail_query')
    @patch('tasks.create_app_for_worker')
    def test_voice_search_task_empty_query(self, mock_create_app, mock_transform, app):
        """Test voice search task with empty query transformation."""
        from tasks import voice_search_task
        
        mock_create_app.return_value = app
        mock_transform.return_value = ""  # Empty query
        
        credentials_json = json.dumps({
            'token': 'test_token',
            'scopes': ['https://www.googleapis.com/auth/gmail.modify']
        })
        
        with app.app_context():
            result = voice_search_task(credentials_json, "знайди листи")
        
        assert result['status'] == 'error'
        assert 'error' in result
        assert 'results' in result
        assert len(result['results']) == 0
    
    @patch('utils.gemini_processor.transform_to_gmail_query')
    @patch('tasks.build_google_services')
    @patch('tasks.create_app_for_worker')
    def test_voice_search_task_service_error(self, mock_create_app, mock_build_services, mock_transform, app):
        """Test voice search task handles service build errors."""
        from tasks import voice_search_task
        
        mock_create_app.return_value = app
        mock_transform.return_value = "from:test"
        mock_build_services.side_effect = Exception("Service error")
        
        credentials_json = json.dumps({
            'token': 'test_token',
            'scopes': ['https://www.googleapis.com/auth/gmail.modify']
        })
        
        with app.app_context():
            result = voice_search_task(credentials_json, "знайди листи")
        
        assert result['status'] == 'error'
        assert 'error' in result
    
    @patch('utils.gmail_api.find_emails_by_query')
    @patch('tasks.build_google_services')
    @patch('utils.gemini_processor.transform_to_gmail_query')
    @patch('tasks.get_message_content')
    @patch('google.oauth2.credentials.Credentials.from_authorized_user_info')
    @patch('tasks.create_app_for_worker')
    def test_voice_search_task_message_content_error(self, mock_create_app, mock_credentials,
                                                      mock_get_content, mock_transform, 
                                                      mock_build_services, mock_find_emails, app):
        """Test voice search task handles message content retrieval errors."""
        from tasks import voice_search_task
        from google.oauth2.credentials import Credentials
        
        mock_create_app.return_value = app
        mock_transform.return_value = "from:test"
        
        # Mock Credentials.from_authorized_user_info to return a mock credentials object
        mock_creds_obj = MagicMock(spec=Credentials)
        mock_credentials.return_value = mock_creds_obj
        
        mock_service = MagicMock()
        mock_build_services.return_value = (mock_service, MagicMock())
        
        mock_find_emails.return_value = [
            {'id': 'msg1', 'threadId': 'thread1'},
            {'id': 'msg2', 'threadId': 'thread2'}
        ]
        
        # First message succeeds, second fails
        mock_get_content.side_effect = [
            ('Email content 1', 'Subject 1'),
            Exception("Content error")
        ]
        
        credentials_json = json.dumps({
            'token': 'test_token',
            'refresh_token': 'test_refresh',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test_client',
            'client_secret': 'test_secret',
            'scopes': ['https://www.googleapis.com/auth/gmail.modify']
        })
        
        with app.app_context():
            result = voice_search_task(credentials_json, "знайди листи")
        
        # Should still return results, with error message for failed ones
        # The function handles exceptions in get_message_content gracefully
        assert result['status'] == 'success', \
            f"Expected 'success', got '{result['status']}' with error: {result.get('error', 'N/A')}"
        assert len(result['results']) == 2
        # Second result should have error placeholder
        assert result['results'][1]['subject'] == 'Error loading'
    
    @patch('tasks.create_app_for_worker')
    def test_voice_search_task_exception_handling(self, mock_create_app, app):
        """Test voice search task handles unexpected exceptions."""
        from tasks import voice_search_task
        
        mock_create_app.side_effect = Exception("Unexpected error")
        
        credentials_json = json.dumps({
            'token': 'test_token',
            'scopes': ['https://www.googleapis.com/auth/gmail.modify']
        })
        
        result = voice_search_task(credentials_json, "знайди листи")
        
        assert result['status'] == 'error'
        assert 'error' in result
        assert 'results' in result


class TestVoiceSearchEndpoint:
    """Integration tests for /voice/search endpoint."""
    
    @patch('server.Redis')
    @patch('server.Queue')
    def test_voice_search_endpoint_success(self, mock_queue_class, mock_redis_class, client, app):
        """Test /voice/search endpoint successfully enqueues task."""
        from server import app as flask_app
        
        # Setup authentication
        with client.session_transaction() as sess:
            sess['credentials'] = json.dumps({
                'token': 'test_token',
                'scopes': ['https://www.googleapis.com/auth/gmail.modify']
            })
        
        # Mock Redis
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.from_url.return_value = mock_redis_instance
        
        # Mock Queue
        mock_queue_instance = MagicMock()
        mock_job = MagicMock()
        mock_job.get_id.return_value = 'job-123'
        mock_queue_instance.enqueue.return_value = mock_job
        mock_queue_class.return_value = mock_queue_instance
        
        # Test request
        response = client.post('/voice/search', 
                              json={'query': 'знайди листи від теста'},
                              content_type='application/json')
        
        assert response.status_code == 202
        data = json.loads(response.data)
        assert data['status'] == 'started'
        assert data['job_id'] == 'job-123'
        assert 'message' in data
    
    def test_voice_search_endpoint_not_authorized(self, client):
        """Test /voice/search endpoint requires authentication."""
        response = client.post('/voice/search',
                              json={'query': 'знайди листи'},
                              content_type='application/json')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Not authorized' in data['message']
    
    def test_voice_search_endpoint_missing_query(self, client, app):
        """Test /voice/search endpoint validates query parameter."""
        with client.session_transaction() as sess:
            sess['credentials'] = json.dumps({'token': 'test_token'})
        
        # Missing query
        response = client.post('/voice/search',
                              json={},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Missing query' in data['message']
    
    def test_voice_search_endpoint_empty_query(self, client, app):
        """Test /voice/search endpoint rejects empty query."""
        with client.session_transaction() as sess:
            sess['credentials'] = json.dumps({'token': 'test_token'})
        
        response = client.post('/voice/search',
                              json={'query': '   '},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'empty' in data['message'].lower()
    
    @patch('server.Redis')
    def test_voice_search_endpoint_redis_error(self, mock_redis_class, client, app):
        """Test /voice/search endpoint handles Redis connection errors."""
        with client.session_transaction() as sess:
            sess['credentials'] = json.dumps({'token': 'test_token'})
        
        # Mock Redis connection error
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.side_effect = Exception("Redis connection error")
        mock_redis_class.from_url.return_value = mock_redis_instance
        
        response = client.post('/voice/search',
                              json={'query': 'знайди листи'},
                              content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['status'] == 'error'

