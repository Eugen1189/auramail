"""
Unit and Integration tests for background task processing.
Uses mocking to avoid real API calls and database operations.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from utils.gmail_api import build_google_services
from utils.gemini_processor import classify_email_with_gemini, get_gemini_client
from utils.db_logger import log_action, init_progress, update_progress, save_report


class TestProcessSingleEmailTask:
    """Test suite for process_single_email_task function."""
    
    @patch('tasks._process_single_email_task_impl')
    @patch('tasks.create_app_for_worker')
    def test_process_single_email_task_uses_app_context(self, mock_create_app, mock_impl, app):
        """Test that process_single_email_task uses Flask app context."""
        from tasks import process_single_email_task
        
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        mock_impl.return_value = {'status': 'success', 'category': 'REVIEW'}
        
        msg = {'id': 'test-msg-id'}
        credentials_json = json.dumps({'token': 'test'})
        gemini_client = MagicMock()
        label_cache = {}
        
        result = process_single_email_task(msg, credentials_json, gemini_client, label_cache)
        
        # Verify app context was used
        mock_app.app_context.assert_called_once()
        mock_impl.assert_called_once()
        assert result['status'] == 'success'
    
    @patch('tasks.build_google_services')
    @patch('tasks.get_message_content')
    @patch('tasks.classify_email_with_gemini')
    @patch('tasks.process_message_action')
    @patch('tasks.log_action')
    @patch('tasks.integrate_with_calendar')
    @patch('tasks.create_app_for_worker')
    def test_process_single_email_task_success_flow(self, mock_create_app, mock_calendar, 
                                                     mock_log, mock_process_action, mock_classify,
                                                     mock_get_content, mock_build_services, app):
        """Test successful email processing flow."""
        from tasks import _process_single_email_task_impl
        
        mock_create_app.return_value = app
        mock_service = MagicMock()
        mock_calendar_service = MagicMock()
        mock_build_services.return_value = (mock_service, mock_calendar_service)
        
        mock_get_content.return_value = ('Email content', 'Test Subject')
        mock_classify.return_value = {
            'category': 'IMPORTANT',
            'action': 'MOVE',
            'label_name': 'AI_IMPORTANT',
            'description': 'Important email',
            'extracted_entities': {}
        }
        mock_process_action.return_value = 'MOVED to AI_IMPORTANT'  # Should not start with "ERROR"
        
        msg = {'id': 'test-msg-id'}
        credentials_json = json.dumps({
            'token': 'test_token',
            'refresh_token': 'test_refresh',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test_client',
            'client_secret': 'test_secret',
            'scopes': ['https://www.googleapis.com/auth/gmail.modify']
        })
        gemini_client = MagicMock()
        label_cache = {'AI_IMPORTANT': 'label-id'}
        
        with app.app_context():
            result = _process_single_email_task_impl(msg, credentials_json, gemini_client, label_cache)
        
        assert result['status'] == 'success'
        assert result['category'] == 'IMPORTANT'
        mock_log.assert_called_once()
        mock_calendar.assert_called_once()
    
    @patch('tasks.build_google_services')
    @patch('tasks.get_message_content')
    @patch('tasks.classify_email_with_gemini')
    @patch('tasks.create_app_for_worker')
    def test_process_single_email_task_handles_ai_error(self, mock_create_app, mock_classify,
                                                         mock_get_content, mock_build_services, app):
        """Test that process_single_email_task handles AI classification errors."""
        from tasks import _process_single_email_task_impl
        
        mock_create_app.return_value = app
        mock_service = MagicMock()
        mock_build_services.return_value = (mock_service, MagicMock())
        mock_get_content.return_value = ('Email content', 'Test Subject')
        
        # Mock AI classification error
        mock_classify.return_value = {
            'error': '429 RESOURCE_EXHAUSTED',
            'category': 'REVIEW'
        }
        
        msg = {'id': 'test-msg-id'}
        credentials_json = json.dumps({'token': 'test'})
        gemini_client = MagicMock()
        label_cache = {}
        
        with app.app_context():
            result = _process_single_email_task_impl(msg, credentials_json, gemini_client, label_cache)
        
        assert result['status'] == 'error'
        assert 'error' in result


class TestBackgroundSortTask:
    """Test suite for background_sort_task function."""
    
    @patch('tasks.get_gemini_client')
    @patch('tasks.build_google_services')
    @patch('tasks.init_progress')
    @patch('tasks.update_progress')
    @patch('tasks.complete_progress')
    @patch('tasks.save_report')
    @patch('tasks._background_sort_task_impl')
    def test_background_sort_task_calls_impl(self, mock_impl, mock_save, mock_complete,
                                             mock_update, mock_init, mock_build, mock_gemini, app):
        """Test that background_sort_task calls implementation function."""
        from tasks import background_sort_task
        
        mock_gemini.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = (mock_service, MagicMock())
        
        # Mock the messages list API call
        mock_messages_list = MagicMock()
        mock_messages_list.execute.return_value = {'messages': []}
        mock_messages = MagicMock()
        mock_messages.list.return_value = mock_messages_list
        mock_users = MagicMock()
        mock_users.messages = MagicMock(return_value=mock_messages)
        mock_service.users = MagicMock(return_value=mock_users)
        
        mock_impl.return_value = {
            'total_processed': 10,
            'important': 2,
            'action_required': 1,
            'newsletter': 3,
            'social': 2,
            'review': 1,
            'deleted': 1,
            'errors': 0
        }
        
        credentials_json = json.dumps({
            'token': 'test_token',
            'refresh_token': 'test_refresh',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test_client',
            'client_secret': 'test_secret',
            'scopes': ['https://www.googleapis.com/auth/gmail.modify']
        })
        
        with app.app_context():
            # background_sort_task calls _background_sort_task_impl which should call save_report
            # But if we mock _background_sort_task_impl, save_report won't be called
            # So we need to test the actual implementation or mock it differently
            result = background_sort_task(credentials_json)
        
        # If impl returns stats, save_report should be called
        # But since we're mocking impl, we need to check if impl was called
        mock_impl.assert_called_once()
        # save_report is called inside _background_sort_task_impl, not background_sort_task
        # So if we mock impl, save_report won't be called
        # This test verifies that background_sort_task calls impl
    
    @patch('tasks.get_gemini_client')
    @patch('tasks.build_google_services')
    def test_background_sort_task_handles_exception(self, mock_build, mock_gemini, app):
        """Test that background_sort_task handles exceptions gracefully."""
        from tasks import _background_sort_task_impl
        
        mock_gemini.return_value = MagicMock()
        mock_service = MagicMock()
        mock_build.side_effect = Exception('Test error - build_google_services failed')
        
        credentials_json = json.dumps({
            'token': 'test_token',
            'refresh_token': 'test_refresh',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test_client',
            'client_secret': 'test_secret',
            'scopes': ['https://www.googleapis.com/auth/gmail.modify']
        })
        
        with app.app_context():
            # _background_sort_task_impl should return None on exception
            result = _background_sort_task_impl(credentials_json)
            # Should return None when exception occurs
            assert result is None


class TestRunTaskInContext:
    """Test suite for run_task_in_context wrapper."""
    
    @patch('tasks.create_app_for_worker')
    def test_run_task_in_context_creates_app_context(self, mock_create_app, app):
        """Test that run_task_in_context creates Flask app context."""
        from tasks import run_task_in_context
        
        mock_create_app.return_value = app
        
        def test_task():
            from flask import has_app_context
            return has_app_context()
        
        result = run_task_in_context(test_task)
        
        assert result is True
        mock_create_app.assert_called_once()

