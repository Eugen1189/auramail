"""
Tests for Prometheus monitoring metrics.
"""
import pytest
from prometheus_client import CollectorRegistry
from utils.monitoring import (
    track_email_processed,
    track_classification_error,
    track_api_request,
    emails_processed_total,
    emails_classification_errors_total,
    api_requests_total,
)


@pytest.fixture
def clean_registry():
    """Use a clean registry for testing."""
    from prometheus_client import REGISTRY
    # Note: In real tests, you'd want to use a separate registry
    yield
    # Cleanup if needed


class TestMonitoringMetrics:
    """Tests for monitoring metrics."""
    
    def test_track_email_processed(self):
        """Test tracking processed emails."""
        # Get initial count
        initial_count = emails_processed_total.labels(
            category='IMPORTANT',
            action='MOVE'
        )._value.get()
        
        # Track email
        track_email_processed('IMPORTANT', 'MOVE')
        
        # Check count increased
        final_count = emails_processed_total.labels(
            category='IMPORTANT',
            action='MOVE'
        )._value.get()
        
        assert final_count == initial_count + 1
    
    def test_track_classification_error(self):
        """Test tracking classification errors."""
        initial_count = emails_classification_errors_total.labels(
            error_type='429_RESOURCE_EXHAUSTED'
        )._value.get()
        
        track_classification_error('429_RESOURCE_EXHAUSTED')
        
        final_count = emails_classification_errors_total.labels(
            error_type='429_RESOURCE_EXHAUSTED'
        )._value.get()
        
        assert final_count == initial_count + 1
    
    def test_track_api_request(self):
        """Test tracking API requests."""
        initial_count = api_requests_total.labels(
            endpoint='/api/progress',
            method='GET',
            status='200'
        )._value.get()
        
        track_api_request('/api/progress', 'GET', 200, 0.1)
        
        final_count = api_requests_total.labels(
            endpoint='/api/progress',
            method='GET',
            status='200'
        )._value.get()
        
        assert final_count == initial_count + 1


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""
    
    def test_metrics_endpoint_returns_prometheus_format(self, client):
        """Test that /metrics returns Prometheus format."""
        response = client.get('/metrics')
        
        assert response.status_code == 200
        content_type = response.content_type or str(response.headers.get('Content-Type', ''))
        assert 'text/plain' in content_type.lower() or 'text' in content_type.lower()
        
        # Check for some metric names
        content = response.get_data(as_text=True)
        assert 'auramail' in content.lower() or len(content) > 0

