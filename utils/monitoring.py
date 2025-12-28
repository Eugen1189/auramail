"""
Prometheus metrics and monitoring utilities for AuraMail.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Response


# Counters - track total occurrences
emails_processed_total = Counter(
    'auramail_emails_processed_total',
    'Total number of emails processed',
    ['category', 'action']
)

emails_classification_errors_total = Counter(
    'auramail_classification_errors_total',
    'Total number of AI classification errors',
    ['error_type']
)

api_requests_total = Counter(
    'auramail_api_requests_total',
    'Total number of API requests',
    ['endpoint', 'method', 'status']
)

# Histograms - track duration
email_processing_duration = Histogram(
    'auramail_email_processing_duration_seconds',
    'Time spent processing a single email',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

sort_job_duration = Histogram(
    'auramail_sort_job_duration_seconds',
    'Time spent processing a full sort job',
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600]
)

api_request_duration = Histogram(
    'auramail_api_request_duration_seconds',
    'Time spent handling API request',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

# Gauges - current values
emails_in_queue = Gauge(
    'auramail_emails_in_queue',
    'Current number of emails in processing queue'
)

active_workers = Gauge(
    'auramail_active_workers',
    'Number of active RQ workers'
)

redis_connection_status = Gauge(
    'auramail_redis_connection_status',
    'Redis connection status (1=connected, 0=disconnected)'
)

database_connection_pool_size = Gauge(
    'auramail_database_pool_size',
    'Current database connection pool size'
)


def track_email_processed(category, action):
    """Track that an email was processed."""
    emails_processed_total.labels(category=category, action=action).inc()


def track_classification_error(error_type):
    """Track an AI classification error."""
    emails_classification_errors_total.labels(error_type=error_type).inc()


def track_api_request(endpoint, method, status_code, duration):
    """Track an API request."""
    api_requests_total.labels(
        endpoint=endpoint,
        method=method,
        status=status_code
    ).inc()
    api_request_duration.labels(endpoint=endpoint).observe(duration)


def metrics_endpoint():
    """Flask route handler for Prometheus metrics."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)











