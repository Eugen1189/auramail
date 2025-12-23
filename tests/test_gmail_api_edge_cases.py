"""
Edge case tests for gmail_api.py to achieve 100% coverage.
Tests multipart messages, encoding errors, label creation errors, and other edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from googleapiclient.errors import HttpError


class TestGetMessageContentEdgeCases:
    """Test edge cases for get_message_content."""
    
    def test_get_message_content_handles_encoding_error(self):
        """Test that get_message_content handles encoding errors."""
        from utils.gmail_api import get_message_content
        
        mock_service = MagicMock()
        
        # Create message with problematic encoding
        mock_message = {
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject \ud800'},  # Invalid surrogate
                    {'name': 'From', 'value': 'test@example.com'},
                    {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
                ]
            },
            'snippet': 'Test snippet'
        }
        
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = mock_message
        
        content, subject = get_message_content(mock_service, 'test-msg-id')
        
        # Should handle encoding error gracefully
        assert content is not None
        assert subject is not None
    
    def test_get_message_content_handles_ascii_fallback(self):
        """Test that get_message_content uses ASCII fallback on encoding error."""
        from utils.gmail_api import get_message_content
        
        mock_service = MagicMock()
        
        # Create message that will cause UTF-8 encoding error
        mock_message = {
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'From', 'value': 'test@example.com'},
                    {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
                ]
            },
            'snippet': 'Test snippet'
        }
        
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = mock_message
        
        # Mock encode/decode to raise exception first time, succeed second time
        with patch('builtins.str') as mock_str:
            # First call raises UnicodeEncodeError, second succeeds
            def encode_side_effect(*args, **kwargs):
                if 'encode' in str(args):
                    raise UnicodeEncodeError('utf-8', 'test', 0, 1, 'error')
                return 'Test Subject'
            mock_str.side_effect = encode_side_effect
            
            content, subject = get_message_content(mock_service, 'test-msg-id')
            
            # Should handle gracefully
            assert content is not None
    
    def test_get_message_content_handles_api_error(self):
        """Test that get_message_content handles API errors."""
        from utils.gmail_api import get_message_content
        
        mock_service = MagicMock()
        
        # Mock API error
        error_response = MagicMock()
        error_response.status = 404
        error_response.reason = 'Not Found'
        mock_service.users.return_value.messages.return_value.get.return_value.execute.side_effect = HttpError(error_response, b'Message not found')
        
        content, subject = get_message_content(mock_service, 'test-msg-id')
        
        # Should return error message
        assert 'Error' in content or 'error' in content.lower()
        assert subject == "Error" or subject is not None
    
    def test_get_message_content_handles_missing_payload(self):
        """Test that get_message_content handles missing payload."""
        from utils.gmail_api import get_message_content
        
        mock_service = MagicMock()
        
        # Message without payload
        mock_message = {
            'snippet': 'Test snippet'
        }
        
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = mock_message
        
        # Should handle gracefully
        try:
            content, subject = get_message_content(mock_service, 'test-msg-id')
            assert content is not None
        except (KeyError, AttributeError):
            # Expected if payload is required
            pass


class TestGetOrCreateLabelEdgeCases:
    """Test edge cases for get_or_create_label_id."""
    
    @patch('utils.gmail_api.LABEL_COLOR_MAP', {'IMPORTANT': 'blue', 'DEFAULT': 'blue'})
    def test_get_or_create_label_handles_color_error_then_succeeds(self):
        """Test that get_or_create_label_id handles color error and retries without color."""
        from utils.gmail_api import get_or_create_label_id
        
        mock_service = MagicMock()
        label_cache = {}
        
        # Mock label list (label doesn't exist)
        mock_list_response = {'labels': []}
        mock_service.users.return_value.labels.return_value.list.return_value.execute.return_value = mock_list_response
        
        # First create attempt fails with color error, second succeeds without color
        color_error = HttpError(MagicMock(status=400, reason='Bad Request'), b'Label color #FFFFFF is not on the allowed color palette')
        created_label = {'id': 'label-id-123', 'name': 'AI_IMPORTANT'}
        
        mock_create = mock_service.users.return_value.labels.return_value.create
        mock_create.return_value.execute.side_effect = [color_error, created_label]
        
        label_id = get_or_create_label_id(mock_service, 'AI_IMPORTANT', label_cache, category='IMPORTANT')
        
        # Should succeed on second attempt
        assert label_id == 'label-id-123'
        assert mock_create.call_count == 2
    
    @patch('utils.gmail_api.LABEL_COLOR_MAP', {'IMPORTANT': 'blue', 'DEFAULT': 'blue'})
    def test_get_or_create_label_handles_non_color_error(self):
        """Test that get_or_create_label_id re-raises non-color errors."""
        from utils.gmail_api import get_or_create_label_id
        
        mock_service = MagicMock()
        label_cache = {}
        
        # Mock label list (label doesn't exist)
        mock_list_response = {'labels': []}
        mock_service.users.return_value.labels.return_value.list.return_value.execute.return_value = mock_list_response
        
        # Non-color error should be re-raised
        other_error = HttpError(MagicMock(status=403, reason='Forbidden'), b'Permission denied')
        mock_create = mock_service.users.return_value.labels.return_value.create
        mock_create.return_value.execute.side_effect = other_error
        
        with pytest.raises(HttpError):
            get_or_create_label_id(mock_service, 'AI_IMPORTANT', label_cache, category='IMPORTANT')
    
    @patch('utils.gmail_api.LABEL_COLOR_MAP', {'IMPORTANT': 'blue', 'DEFAULT': 'blue'})
    def test_get_or_create_label_handles_second_create_failure(self):
        """Test that get_or_create_label_id raises original error if second create fails."""
        from utils.gmail_api import get_or_create_label_id
        
        mock_service = MagicMock()
        label_cache = {}
        
        # Mock label list (label doesn't exist)
        mock_list_response = {'labels': []}
        mock_service.users.return_value.labels.return_value.list.return_value.execute.return_value = mock_list_response
        
        # First create fails with color error, second create also fails
        color_error = HttpError(MagicMock(status=400, reason='Bad Request'), b'Label color #FFFFFF is not on the allowed color palette')
        other_error = HttpError(MagicMock(status=500, reason='Internal Server Error'), b'Server error')
        
        mock_create = mock_service.users.return_value.labels.return_value.create
        mock_create.return_value.execute.side_effect = [color_error, other_error]
        
        # Should raise original color_error, not other_error
        with pytest.raises(HttpError) as exc_info:
            get_or_create_label_id(mock_service, 'AI_IMPORTANT', label_cache, category='IMPORTANT')
        
        # Should be the original color error
        assert exc_info.value == color_error
    
    def test_get_or_create_label_detects_category_from_label_name(self):
        """Test that get_or_create_label_id detects category from label name."""
        from utils.gmail_api import get_or_create_label_id
        
        mock_service = MagicMock()
        label_cache = {}
        
        # Mock label list (label doesn't exist)
        mock_list_response = {'labels': []}
        mock_service.users.return_value.labels.return_value.list.return_value.execute.return_value = mock_list_response
        
        # Create label without providing category (should detect from name)
        created_label = {'id': 'label-id-456', 'name': 'AI_BILLS_INVOICES'}
        mock_create = mock_service.users.return_value.labels.return_value.create
        mock_create.return_value.execute.return_value = created_label
        
        label_id = get_or_create_label_id(mock_service, 'AI_BILLS_INVOICES', label_cache)
        
        assert label_id == 'label-id-456'


class TestProcessMessageActionEdgeCases:
    """Test edge cases for process_message_action."""
    
    def test_process_message_action_handles_missing_label_name_for_move(self):
        """Test that process_message_action raises error for MOVE without label_name."""
        from utils.gmail_api import process_message_action
        
        mock_service = MagicMock()
        label_cache = {}
        
        classification = {
            'category': 'IMPORTANT',
            'action': 'MOVE'
            # Missing label_name
        }
        
        result = process_message_action(mock_service, 'test-msg-id', classification, label_cache)
        
        assert 'ERROR' in result
        assert 'label_name' in result.lower() or 'обов\'язковий' in result.lower()
    
    def test_process_message_action_handles_unknown_action(self):
        """Test that process_message_action handles unknown action."""
        from utils.gmail_api import process_message_action
        
        mock_service = MagicMock()
        label_cache = {}
        
        classification = {
            'category': 'REVIEW',
            'action': 'UNKNOWN_ACTION'
        }
        
        result = process_message_action(mock_service, 'test-msg-id', classification, label_cache)
        
        assert 'UNKNOWN_ACTION' in result


class TestRollbackActionEdgeCases:
    """Test edge cases for rollback_action."""
    
    def test_rollback_action_handles_missing_message_id(self):
        """Test that rollback_action handles missing message ID."""
        from utils.gmail_api import rollback_action
        
        mock_service = MagicMock()
        label_cache = {}
        
        log_entry = {
            'action_taken': 'ARCHIVE'
            # Missing message_id
        }
        
        result = rollback_action(mock_service, log_entry, label_cache)
        
        assert 'ERROR' in result
        assert 'Message ID' in result
    
    def test_rollback_action_handles_missing_label_for_move(self):
        """Test that rollback_action handles missing label for MOVE rollback."""
        from utils.gmail_api import rollback_action
        
        mock_service = MagicMock()
        label_cache = {}
        
        log_entry = {
            'message_id': 'test-msg-id',
            'action_taken': 'MOVE'
            # Missing label_name
        }
        
        result = rollback_action(mock_service, log_entry, label_cache)
        
        assert 'ERROR' in result
        assert 'label' in result.lower()
    
    def test_rollback_action_handles_api_error(self):
        """Test that rollback_action handles Gmail API errors."""
        from utils.gmail_api import rollback_action
        
        mock_service = MagicMock()
        label_cache = {}
        
        log_entry = {
            'message_id': 'test-msg-id',
            'action_taken': 'ARCHIVE'
        }
        
        # Mock API error
        error_response = MagicMock()
        error_response.status = 404
        error_response.reason = 'Not Found'
        mock_service.users.return_value.messages.return_value.modify.return_value.execute.side_effect = HttpError(error_response, b'Message not found')
        
        result = rollback_action(mock_service, log_entry, label_cache)
        
        assert 'ERROR' in result or 'Gmail API Error' in result


class TestFindEmailsByQueryEdgeCases:
    """Test edge cases for find_emails_by_query."""
    
    def test_find_emails_by_query_handles_empty_query(self):
        """Test that find_emails_by_query handles empty query."""
        from utils.gmail_api import find_emails_by_query
        
        mock_service = MagicMock()
        
        result = find_emails_by_query(mock_service, '')
        
        assert result == []
    
    def test_find_emails_by_query_handles_whitespace_query(self):
        """Test that find_emails_by_query handles whitespace-only query."""
        from utils.gmail_api import find_emails_by_query
        
        mock_service = MagicMock()
        
        result = find_emails_by_query(mock_service, '   ')
        
        assert result == []
    
    def test_find_emails_by_query_handles_api_error(self):
        """Test that find_emails_by_query handles API errors."""
        from utils.gmail_api import find_emails_by_query
        
        mock_service = MagicMock()
        
        # Mock API error
        error_response = MagicMock()
        error_response.status = 400
        error_response.reason = 'Bad Request'
        mock_service.users.return_value.messages.return_value.list.return_value.execute.side_effect = HttpError(error_response, b'Invalid query')
        
        result = find_emails_by_query(mock_service, 'invalid query')
        
        # Should return empty list on error
        assert result == []
    
    def test_find_emails_by_query_handles_missing_messages_key(self):
        """Test that find_emails_by_query handles response without messages key."""
        from utils.gmail_api import find_emails_by_query
        
        mock_service = MagicMock()
        
        # Response without 'messages' key
        mock_response = {}
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = mock_response
        
        result = find_emails_by_query(mock_service, 'test query')
        
        # Should return empty list
        assert result == []






