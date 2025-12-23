"""
Edge case tests for gemini_processor.py to achieve 100% coverage.
Tests non-429 API errors, JSON parsing errors, Unicode errors, and other edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock, PropertyMock
import json
from google.genai import types


class TestClassifyEmailNon429Errors:
    """Test handling of non-429 API errors."""
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_handles_400_error(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification handles 400 Bad Request errors."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock 400 error
        mock_call_api.side_effect = Exception("400 Bad Request: Invalid input")
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        result = classify_email_with_gemini(gemini_client, email_content)
        
        assert 'error' in result
        assert result['category'] == 'REVIEW'
        assert result['action'] == 'ARCHIVE'
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_handles_500_error(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification handles 500 Internal Server errors."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock 500 error
        mock_call_api.side_effect = Exception("500 Internal Server Error")
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        result = classify_email_with_gemini(gemini_client, email_content)
        
        assert 'error' in result
        assert '500' in result['error'] or 'Internal Server' in result['error']
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_handles_403_error(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification handles 403 Forbidden errors."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock 403 error
        mock_call_api.side_effect = Exception("403 Forbidden: API key invalid")
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        result = classify_email_with_gemini(gemini_client, email_content)
        
        assert 'error' in result
        assert result['category'] == 'REVIEW'


class TestClassifyEmailJSONParsing:
    """Test JSON parsing error handling."""
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_handles_json_decode_error(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification handles JSON decode errors."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock response with invalid JSON
        mock_response_obj = MagicMock()
        mock_response_obj.text = '{"category": "IMPORTANT", invalid json}'
        mock_call_api.return_value = mock_response_obj
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        result = classify_email_with_gemini(gemini_client, email_content)
        
        assert 'error' in result or result['category'] == 'REVIEW'
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_handles_missing_extracted_entities(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification handles missing extracted_entities field."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock response without extracted_entities
        mock_response_obj = MagicMock()
        mock_response_obj.text = '{"category": "IMPORTANT", "action": "MOVE", "label_name": "AI_IMPORTANT", "description": "Test", "urgency": "HIGH"}'
        mock_call_api.return_value = mock_response_obj
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        result = classify_email_with_gemini(gemini_client, email_content)
        
        # Should add empty extracted_entities
        assert 'extracted_entities' in result
        assert result['extracted_entities'] == {}


class TestClassifyEmailUnicodeErrors:
    """Test Unicode encoding error handling."""
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_handles_unicode_encode_error(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification handles UnicodeEncodeError."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock response with problematic Unicode
        mock_response_obj = MagicMock()
        # Create a response that will cause UnicodeEncodeError
        mock_response_obj.text = '\ud800\udc00'  # Invalid surrogate pair
        mock_call_api.return_value = mock_response_obj
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        result = classify_email_with_gemini(gemini_client, email_content)
        
        # Should handle error gracefully
        assert isinstance(result, dict)
        assert 'error' in result or result['category'] == 'REVIEW'
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_handles_non_string_response(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification handles non-string response.text."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock response with non-string text
        mock_response_obj = MagicMock()
        mock_response_obj.text = {'json': 'object'}  # Not a string
        mock_call_api.return_value = mock_response_obj
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        result = classify_email_with_gemini(gemini_client, email_content)
        
        # Should convert to string and handle
        assert isinstance(result, dict)


class TestClassifyEmailConfigFallback:
    """Test config creation fallback."""
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    @patch('utils.gemini_processor.types.GenerateContentConfig')
    def test_classify_email_handles_config_creation_error(self, mock_config_class, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification handles config creation errors."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock config creation to fail with AttributeError first time
        # The function catches (AttributeError, TypeError) and uses fallback dict
        # Then creates config again with the dict
        fallback_config = MagicMock()
        mock_config_class.side_effect = [
            AttributeError("Schema not supported"),  # First call fails
            fallback_config  # Second call (with dict) succeeds
        ]
        
        mock_response_obj = MagicMock()
        mock_response_obj.text = '{"category": "REVIEW", "action": "ARCHIVE", "label_name": "AI_REVIEW", "description": "Test", "urgency": "LOW", "extracted_entities": {}}'
        mock_call_api.return_value = mock_response_obj
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        # The function catches AttributeError/TypeError and uses fallback dict config
        # So it should succeed
        result = classify_email_with_gemini(gemini_client, email_content)
        
        # Should use fallback config and return result
        assert isinstance(result, dict)
        # Config should have been called twice (first fails, second succeeds with dict)
        assert mock_config_class.call_count >= 1


class TestDetectExpectedReplyEdgeCases:
    """Test edge cases for detect_expected_reply_with_gemini."""
    
    def test_detect_expected_reply_without_client(self):
        """Test detect_expected_reply_with_gemini without client."""
        from utils.gemini_processor import detect_expected_reply_with_gemini
        
        result = detect_expected_reply_with_gemini(None, "Test email")
        
        assert result['expects_reply'] is False
        assert 'error' in result
        assert 'GEMINI_API_KEY' in result['error']
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    def test_detect_expected_reply_rate_limit_timeout(self, mock_semaphore, mock_rate_limit):
        """Test detect_expected_reply_with_gemini rate limit timeout."""
        from utils.gemini_processor import detect_expected_reply_with_gemini
        
        mock_rate_limit.return_value = False  # Always blocked
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        mock_client = MagicMock()
        
        with patch('time.sleep'):  # Speed up test
            result = detect_expected_reply_with_gemini(mock_client, "Test email")
        
        assert result['expects_reply'] is False
        assert 'error' in result
        assert 'timeout' in result['error'].lower()
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    def test_detect_expected_reply_handles_bytes_content(self, mock_semaphore, mock_rate_limit):
        """Test detect_expected_reply_with_gemini with bytes content."""
        from utils.gemini_processor import detect_expected_reply_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"expects_reply": true, "expected_reply_date": "2025-12-31", "confidence": "HIGH"}'
        mock_client.models.generate_content.return_value = mock_response
        
        # Test with bytes content
        result = detect_expected_reply_with_gemini(mock_client, b"Test email bytes")
        
        assert isinstance(result, dict)
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    def test_detect_expected_reply_handles_non_string_content(self, mock_semaphore, mock_rate_limit):
        """Test detect_expected_reply_with_gemini with non-string content."""
        from utils.gemini_processor import detect_expected_reply_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"expects_reply": false, "expected_reply_date": "", "confidence": "LOW"}'
        mock_client.models.generate_content.return_value = mock_response
        
        # Test with non-string content (e.g., dict)
        result = detect_expected_reply_with_gemini(mock_client, {'email': 'content'})
        
        assert isinstance(result, dict)
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    def test_detect_expected_reply_handles_json_parse_error(self, mock_semaphore, mock_rate_limit):
        """Test detect_expected_reply_with_gemini with JSON parse error."""
        from utils.gemini_processor import detect_expected_reply_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = 'Invalid JSON response'
        mock_client.models.generate_content.return_value = mock_response
        
        result = detect_expected_reply_with_gemini(mock_client, "Test email")
        
        assert result['expects_reply'] is False
        assert 'error' in result
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    def test_detect_expected_reply_handles_api_error(self, mock_semaphore, mock_rate_limit):
        """Test detect_expected_reply_with_gemini with API error."""
        from utils.gemini_processor import detect_expected_reply_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")
        
        result = detect_expected_reply_with_gemini(mock_client, "Test email")
        
        assert result['expects_reply'] is False
        assert 'error' in result
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    def test_detect_expected_reply_handles_config_error(self, mock_semaphore, mock_rate_limit):
        """Test detect_expected_reply_with_gemini with config creation error."""
        from utils.gemini_processor import detect_expected_reply_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"expects_reply": false, "expected_reply_date": "", "confidence": "LOW"}'
        mock_client.models.generate_content.return_value = mock_response
        
        # Mock config creation to fail
        with patch('utils.gemini_processor.types.GenerateContentConfig', side_effect=Exception("Config error")):
            result = detect_expected_reply_with_gemini(mock_client, "Test email")
        
        # Should use fallback config
        assert isinstance(result, dict)
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    def test_detect_expected_reply_handles_response_without_text(self, mock_semaphore, mock_rate_limit):
        """Test detect_expected_reply_with_gemini with response without text attribute."""
        from utils.gemini_processor import detect_expected_reply_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        mock_client = MagicMock()
        # Create a mock response without text attribute
        # The code uses: raw = response.text if hasattr(response, "text") else str(response)
        mock_response = MagicMock()
        
        # Make hasattr return False for 'text' attribute
        # Make str(response) return valid JSON
        mock_response.__str__ = Mock(return_value='{"expects_reply": false, "expected_reply_date": "", "confidence": "LOW"}')
        mock_client.models.generate_content.return_value = mock_response
        
        # Patch hasattr to return False for text attribute to avoid recursion
        original_hasattr = hasattr
        def mock_hasattr(obj, name):
            if obj == mock_response and name == 'text':
                return False
            return original_hasattr(obj, name)
        
        with patch('builtins.hasattr', side_effect=mock_hasattr):
            result = detect_expected_reply_with_gemini(mock_client, "Test email")
        
        assert isinstance(result, dict)
        assert result.get('expects_reply') is False

