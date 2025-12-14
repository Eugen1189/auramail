"""
Structured logging configuration for AuraMail.
Uses structlog for better log formatting and integration with ELK stack.
"""
import logging
import sys
import structlog
# Note: pythonjsonlogger.jsonlogger has been moved to pythonjsonlogger.json
# but we use structlog's JSONRenderer, so this import is not needed
# from pythonjsonlogger import jsonlogger  # Deprecated, using structlog instead


def setup_structured_logging():
    """
    Configure structured logging with structlog.
    Returns configured logger.
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()  # JSON format for ELK stack
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    
    return structlog.get_logger()


def get_logger(name=None):
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Structured logger instance
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


# Example usage:
# logger = get_logger(__name__)
# logger.info("email_processed", msg_id="123", category="IMPORTANT", action="MOVE")
# logger.error("classification_failed", msg_id="456", error="429 RESOURCE_EXHAUSTED")

