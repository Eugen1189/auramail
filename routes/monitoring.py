"""
Monitoring routes for health checks and metrics.
"""
from flask import Blueprint, jsonify
from redis import Redis

from config import REDIS_URL
from utils.monitoring import metrics_endpoint
from database import db

monitoring_bp = Blueprint('monitoring', __name__)


@monitoring_bp.route('/health')
def health():
    """
    Health check endpoint for Docker/Kubernetes.
    Returns 200 OK if service is healthy.
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            service:
              type: string
              example: AuraMail
            version:
              type: string
              example: "1.0.0"
      503:
        description: Service is unhealthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: unhealthy
            error:
              type: string
    """
    try:
        redis_conn = Redis.from_url(REDIS_URL)
        redis_conn.ping()
        
        db.session.execute(db.text('SELECT 1'))
        
        return jsonify({
            'status': 'healthy',
            'service': 'AuraMail',
            'version': '1.0.0'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@monitoring_bp.route('/metrics')
def metrics():
    """
    Prometheus metrics endpoint.
    ---
    tags:
      - Monitoring
    produces:
      - text/plain
    responses:
      200:
        description: Prometheus metrics in text format
        schema:
          type: string
    """
    return metrics_endpoint()


@monitoring_bp.route('/swagger')
@monitoring_bp.route('/docs')
def swagger_redirect():
    """Redirect to Swagger UI documentation."""
    from flask import redirect
    return redirect('/api-docs')

