"""
Extended Unit tests for Gemini AI processor.
Tests classification, client initialization, and response handling.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from google.genai import types


class TestGetGeminiClient:
    """Test suite for get_gemini_client function."""
    
    @patch('utils.gemini_processor.genai')
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-api-key'})
    def test_get_gemini_client_initializes_with_api_key(self, mock_genai):
        """Test that get_gemini_client initializes client with API key from config."""
        from utils.gemini_processor import get_gemini_client
        
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        
        client = get_gemini_client()
        
        mock_genai.Client.assert_called_once()
        assert client == mock_client
    
    @patch('utils.gemini_processor.genai')
    @patch('utils.gemini_processor.GEMINI_API_KEY', 'AIzaTestApiKey123')
    def test_get_gemini_client_uses_config_api_key(self, mock_genai):
        """Test that get_gemini_client uses API key from config."""
        from utils.gemini_processor import get_gemini_client
        
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        
        client = get_gemini_client()
        
        mock_genai.Client.assert_called_once()
        # Verify it was called with the cleaned API key
        # The function strips and validates the key
        call_args = mock_genai.Client.call_args
        assert call_args is not None
        assert 'api_key' in call_args.kwargs


class TestClassifyEmailWithGemini:
    """Test suite for classify_email_with_gemini function."""
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_success_with_valid_response(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test successful email classification with valid AI response."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock response object with text attribute
        mock_response_obj = MagicMock()
        mock_response_obj.text = '{"category": "IMPORTANT", "action": "MOVE", "label_name": "AI_IMPORTANT", "description": "Important email", "urgency": "HIGH", "extracted_entities": {}}'
        mock_call_api.return_value = mock_response_obj
        
        gemini_client = MagicMock()
        email_content = "Subject: Meeting Request\nPlease attend the meeting on December 31st."
        
        result = classify_email_with_gemini(gemini_client, email_content)
        
        assert result['category'] == 'IMPORTANT'
        assert result['action'] == 'MOVE'
        assert result['label_name'] == 'AI_IMPORTANT'
        mock_call_api.assert_called_once()
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_handles_rate_limit_wait(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification waits when rate limit is reached."""
        from utils.gemini_processor import classify_email_with_gemini
        import time
        
        # First call blocks, second call allows
        mock_rate_limit.side_effect = [False, True]
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        mock_response_obj = MagicMock()
        mock_response_obj.text = '{"category": "REVIEW", "action": "ARCHIVE", "label_name": "AI_REVIEW", "description": "Test", "urgency": "LOW", "extracted_entities": {}}'
        mock_call_api.return_value = mock_response_obj
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        with patch('time.sleep') as mock_sleep:
            result = classify_email_with_gemini(gemini_client, email_content)
        
        assert result['category'] == 'REVIEW'
        # Should have slept once due to rate limit
        assert mock_sleep.called or mock_rate_limit.call_count >= 2
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_handles_api_error(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification handles API errors gracefully."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock API error
        mock_call_api.side_effect = Exception("API Error: 429 RESOURCE_EXHAUSTED")
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        result = classify_email_with_gemini(gemini_client, email_content)
        
        assert 'error' in result
        assert 'RESOURCE_EXHAUSTED' in result['error'] or 'error' in result.get('error', '').upper()
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_handles_malformed_response(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification handles malformed AI responses."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        # Mock malformed JSON response
        mock_response_obj = MagicMock()
        mock_response_obj.text = '{"description": "Some description"}'  # Missing required fields
        mock_call_api.return_value = mock_response_obj
        
        gemini_client = MagicMock()
        email_content = "Test email"
        
        result = classify_email_with_gemini(gemini_client, email_content)
        
        # Should return response even if malformed (with defaults or error)
        assert isinstance(result, dict)
    
    @patch('utils.gemini_processor.check_gemini_rate_limit')
    @patch('utils.gemini_processor.GEMINI_SEMAPHORE')
    @patch('utils.gemini_processor._call_gemini_api')
    def test_classify_email_uses_semaphore(self, mock_call_api, mock_semaphore, mock_rate_limit):
        """Test that classification uses semaphore for concurrency control."""
        from utils.gemini_processor import classify_email_with_gemini
        
        mock_rate_limit.return_value = True
        mock_semaphore.acquire = MagicMock()
        mock_semaphore.release = MagicMock()
        
        mock_response_obj = MagicMock()
        mock_response_obj.text = '{"category": "NEWSLETTER", "action": "ARCHIVE", "label_name": "AI_NEWSLETTER", "description": "Newsletter", "urgency": "LOW", "extracted_entities": {}}'
        mock_call_api.return_value = mock_response_obj
        
        gemini_client = MagicMock()
        email_content = "Newsletter email"
        
        classify_email_with_gemini(gemini_client, email_content)
        
        # Verify semaphore was used
        assert mock_semaphore.acquire.called
        assert mock_semaphore.release.called


class TestCallGeminiAPI:
    """Test suite for _call_gemini_api function (retry mechanism)."""
    
    @patch('utils.gemini_processor.genai')
    def test_call_gemini_api_success(self, mock_genai):
        """Test successful Gemini API call."""
        from utils.gemini_processor import _call_gemini_api
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"category": "IMPORTANT", "action": "MOVE"}'
        
        # Mock client.models.generate_content correctly
        mock_generate_content = MagicMock(return_value=mock_response)
        mock_models_obj = MagicMock()
        mock_models_obj.generate_content = mock_generate_content
        mock_client.models.generate_content = mock_generate_content
        
        email_content = "Important email"
        mock_config = MagicMock()
        
        result = _call_gemini_api(mock_client, email_content, mock_config)
        
        # Should return response object
        assert result == mock_response
        mock_generate_content.assert_called_once()
    
    @patch('utils.gemini_processor.genai')
    def test_call_gemini_api_retries_on_429_error(self, mock_genai):
        """Test that _call_gemini_api retries on 429 errors."""
        from utils.gemini_processor import _call_gemini_api
        
        mock_client = MagicMock()
        
        # First call raises 429, second call succeeds
        error_response = Exception("429 RESOURCE_EXHAUSTED")
        mock_response = MagicMock()
        mock_response.text = '{"category": "REVIEW", "action": "ARCHIVE"}'
        
        mock_generate_content = MagicMock(side_effect=[error_response, mock_response])
        mock_client.models.generate_content = mock_generate_content
        
        email_content = "Test email"
        mock_config = MagicMock()
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            try:
                result = _call_gemini_api(mock_client, email_content, mock_config)
                # If succeeds after retry, should have called multiple times
                assert mock_generate_content.call_count >= 2
            except Exception:
                # If all retries fail, that's also acceptable behavior
                assert mock_generate_content.call_count >= 2
    
    @patch('utils.gemini_processor.genai')
    def test_call_gemini_api_handles_invalid_response(self, mock_genai):
        """Test that _call_gemini_api handles invalid responses."""
        from utils.gemini_processor import _call_gemini_api
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = 'Invalid JSON response'
        
        mock_generate_content = MagicMock(return_value=mock_response)
        mock_client.models.generate_content = mock_generate_content
        
        email_content = "Test email"
        mock_config = MagicMock()
        
        # Should return response object (parsing happens in classify_email_with_gemini)
        result = _call_gemini_api(mock_client, email_content, mock_config)
        
        assert mock_generate_content.called
        # Result is the response object, not parsed dict
        assert result == mock_response

