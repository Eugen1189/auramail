"""
Unit tests for Gemini API rate limiter.
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from utils.gemini_processor import check_gemini_rate_limit, MAX_CALLS_PER_MINUTE


class TestRateLimiter:
    """Test suite for rate limiter functionality."""
    
    @patch('utils.gemini_processor.redis_client')
    def test_rate_limit_allows_request_when_under_limit(self, mock_redis):
        """Test that rate limiter allows requests when under limit."""
        # Setup: Under limit (current calls < MAX_CALLS_PER_MINUTE)
        mock_redis.zcard.return_value = MAX_CALLS_PER_MINUTE - 1
        
        result = check_gemini_rate_limit()
        
        assert result is True
        mock_redis.zremrangebyscore.assert_called_once()
        mock_redis.zadd.assert_called_once()
        mock_redis.expire.assert_called_once()
    
    @patch('utils.gemini_processor.redis_client')
    def test_rate_limit_blocks_request_when_at_limit(self, mock_redis):
        """Test that rate limiter blocks requests when at limit."""
        # Setup: At limit (current calls >= MAX_CALLS_PER_MINUTE)
        mock_redis.zcard.return_value = MAX_CALLS_PER_MINUTE
        
        result = check_gemini_rate_limit()
        
        assert result is False
        mock_redis.zremrangebyscore.assert_called_once()
        mock_redis.zadd.assert_not_called()  # Should not add new request
    
    @patch('utils.gemini_processor.redis_client')
    def test_rate_limit_removes_old_entries(self, mock_redis):
        """Test that rate limiter removes entries older than 60 seconds."""
        mock_redis.zcard.return_value = 0
        
        check_gemini_rate_limit()
        
        # Verify old entries are removed (cutoff_time = now - 60)
        mock_redis.zremrangebyscore.assert_called_once()
        call_args = mock_redis.zremrangebyscore.call_args
        assert call_args[0][1] == 0  # min score
        assert call_args[0][2] < time.time()  # max score (cutoff_time)
    
    @patch('utils.gemini_processor.redis_client')
    def test_rate_limit_fallback_on_redis_error(self, mock_redis):
        """Test that rate limiter allows request if Redis is unavailable (fallback)."""
        # Setup: Redis raises exception
        mock_redis.zcard.side_effect = Exception("Redis connection error")
        
        result = check_gemini_rate_limit()
        
        # Should allow request as fallback
        assert result is True
    
    @patch('utils.gemini_processor.redis_client')
    def test_rate_limit_sets_ttl(self, mock_redis):
        """Test that rate limiter sets TTL for Redis key."""
        mock_redis.zcard.return_value = 0
        
        check_gemini_rate_limit()
        
        # Verify TTL is set to 120 seconds
        mock_redis.expire.assert_called_once()
        call_args = mock_redis.expire.call_args
        assert call_args[0][1] == 120  # TTL in seconds











