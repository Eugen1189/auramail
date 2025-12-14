"""
Unit tests for cache helper functions.
Tests cache invalidation logic and error handling.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestInvalidateDashboardCache:
    """Test suite for invalidate_dashboard_cache function."""
    
    @patch('utils.cache_helper.cache')
    def test_invalidate_dashboard_cache_success(self, mock_cache):
        """Test successful cache invalidation."""
        from utils.cache_helper import invalidate_dashboard_cache
        
        # Execute
        invalidate_dashboard_cache()
        
        # Verify cache.delete was called for each key
        assert mock_cache.delete.call_count == 3
        mock_cache.delete.assert_any_call('dashboard_index')
        mock_cache.delete.assert_any_call('report_page')
        mock_cache.delete.assert_any_call('api_progress')
    
    @patch('utils.cache_helper.cache')
    def test_invalidate_dashboard_cache_handles_error(self, mock_cache):
        """Test cache invalidation handles errors gracefully."""
        from utils.cache_helper import invalidate_dashboard_cache
        
        # Mock cache.delete to raise exception
        mock_cache.delete.side_effect = Exception("Cache error")
        
        # Should not raise exception
        try:
            invalidate_dashboard_cache()
        except Exception:
            pytest.fail("invalidate_dashboard_cache should handle errors gracefully")


class TestInvalidateStatsCache:
    """Test suite for invalidate_stats_cache function."""
    
    @patch('utils.cache_helper.cache')
    def test_invalidate_stats_cache_success(self, mock_cache):
        """Test successful statistics cache invalidation."""
        from utils.cache_helper import invalidate_stats_cache
        
        # Execute
        invalidate_stats_cache()
        
        # Verify cache.delete was called for each key
        assert mock_cache.delete.call_count == 2
        mock_cache.delete.assert_any_call('dashboard_index')
        mock_cache.delete.assert_any_call('report_page')
        # Should NOT delete api_progress (verify it wasn't called with this key)
        delete_calls = [call[0][0] if call[0] else None for call in mock_cache.delete.call_args_list]
        assert 'api_progress' not in delete_calls
    
    @patch('utils.cache_helper.cache')
    def test_invalidate_stats_cache_handles_error(self, mock_cache):
        """Test statistics cache invalidation handles errors gracefully."""
        from utils.cache_helper import invalidate_stats_cache
        
        # Mock cache.delete to raise exception
        mock_cache.delete.side_effect = Exception("Cache error")
        
        # Should not raise exception
        try:
            invalidate_stats_cache()
        except Exception:
            pytest.fail("invalidate_stats_cache should handle errors gracefully")
    
    @patch('utils.cache_helper.cache')
    def test_invalidate_stats_cache_partial_failure(self, mock_cache):
        """Test statistics cache invalidation handles partial failures."""
        from utils.cache_helper import invalidate_stats_cache
        
        # Mock first call to succeed, second to fail
        call_count = [0]
        def side_effect(key):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Second delete failed")
        
        mock_cache.delete.side_effect = side_effect
        
        # Should not raise exception
        try:
            invalidate_stats_cache()
        except Exception:
            pytest.fail("invalidate_stats_cache should handle partial failures gracefully")
        
        # Should have attempted both deletions
        assert mock_cache.delete.call_count == 2

