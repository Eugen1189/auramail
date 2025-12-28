"""
API routes for analytics, follow-up, and other API endpoints.
"""
import json
from flask import Blueprint, jsonify, session, request
from redis import Redis
from rq import Queue

from config import REDIS_URL
from utils.logging_config import get_logger
from utils.validators import validate_int_param

logger = get_logger(__name__)

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/analytics/roi')
def api_analytics_roi():
    """
    Returns ROI analytics data.
    ---
    tags:
      - Analytics
    security:
      - sessionAuth: []
    parameters:
      - name: days
        in: query
        type: integer
        default: 30
        description: Number of days to analyze
    responses:
      200:
        description: ROI analytics data
        schema:
          type: object
          properties:
            period_days:
              type: integer
            cost_saved_usd:
              type: number
            ai_cost_usd:
              type: number
            net_savings_usd:
              type: number
            roi_percentage:
              type: number
      500:
        description: Error calculating ROI
    """
    try:
        from utils.analytics import calculate_roi
        # Validate days parameter
        days = validate_int_param('days', min_value=1, max_value=365, default=30)
        roi_data = calculate_roi(days)
        return jsonify(roi_data)
    except ValueError as e:
        logger.warning(f"Validation error in ROI endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'period_days': 30,
            'cost_saved_usd': 0,
            'ai_cost_usd': 0,
            'net_savings_usd': 0,
            'roi_percentage': 0
        }), 500


@api_bp.route('/api/analytics/time-savings')
def api_analytics_time_savings():
    """
    Returns time savings analytics data.
    ---
    tags:
      - Analytics
    security:
      - sessionAuth: []
    parameters:
      - name: days
        in: query
        type: integer
        default: 30
        description: Number of days to analyze
    responses:
      200:
        description: Time savings analytics data
        schema:
          type: object
          properties:
            period_days:
              type: integer
            emails_processed:
              type: integer
            total_hours_saved:
              type: number
            cost_saved_usd:
              type: number
      500:
        description: Error calculating time savings
    """
    try:
        from utils.analytics import calculate_time_savings
        # Validate days parameter
        days = validate_int_param('days', min_value=1, max_value=365, default=30)
        time_data = calculate_time_savings(days)
        return jsonify(time_data)
    except ValueError as e:
        logger.warning(f"Validation error in time-savings endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'period_days': 30,
            'emails_processed': 0,
            'total_hours_saved': 0,
            'cost_saved_usd': 0
        }), 400
    except Exception as e:
        logger.warning(f"Validation error in time-savings endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'period_days': 30,
            'emails_processed': 0,
            'total_hours_saved': 0,
            'cost_saved_usd': 0
        }), 500


@api_bp.route('/api/analytics/chart-data')
def api_analytics_chart_data():
    """
    Returns chart data for time savings visualization.
    ---
    tags:
      - Analytics
    security:
      - sessionAuth: []
    parameters:
      - name: days
        in: query
        type: integer
        default: 30
        description: Number of days to analyze
      - name: type
        in: query
        type: string
        enum: [time-savings, category-distribution]
        default: time-savings
        description: Type of chart data
    responses:
      200:
        description: Chart data
        schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
            datasets:
              type: array
              items:
                type: object
      500:
        description: Error generating chart data
    """
    try:
        from utils.analytics import get_time_savings_chart_data
        from utils.validators import validate_string_param
        # Validate parameters
        days = validate_int_param('days', min_value=1, max_value=365, default=30)
        chart_type = validate_string_param('type', default='time-savings', 
                                          pattern=r'^(time-savings|roi|categories)$')
        
        if chart_type == 'time-savings':
            chart_data = get_time_savings_chart_data(days)
        else:
            chart_data = {'labels': [], 'datasets': []}
        
        return jsonify(chart_data)
    except ValueError as e:
        logger.warning(f"Validation error in chart-data endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'labels': [],
            'datasets': []
        }), 400
    except Exception as e:
        logger.error(f"Error generating chart data: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'labels': [],
            'datasets': []
        }), 500


@api_bp.route('/api/sent_hook', methods=['POST'])
def handle_sent_hook():
    """
    Hook for sent emails. Expects JSON with msg_id.
    Enqueues process_sent_email_task to detect expected reply and log follow-up metadata.
    ---
    tags:
      - Follow-up
    security:
      - sessionAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - msg_id
          properties:
            msg_id:
              type: string
              description: Gmail message ID of sent email
    responses:
      202:
        description: Sent email analysis enqueued
        schema:
          type: object
          properties:
            status:
              type: string
              example: started
            job_id:
              type: string
            message:
              type: string
      400:
        description: Missing msg_id
      401:
        description: Not authorized
      500:
        description: Error enqueueing task
    """
    if 'credentials' not in session:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 401

    data = request.get_json()
    if not data or 'msg_id' not in data:
        return jsonify({'status': 'error', 'message': 'Missing msg_id'}), 400

    msg_id = data.get('msg_id')
    if not msg_id:
        return jsonify({'status': 'error', 'message': 'msg_id cannot be empty'}), 400

    try:
        redis_conn = Redis.from_url(REDIS_URL)
        redis_conn.ping()
        q = Queue(connection=redis_conn)
        
        from tasks.email_processing import process_sent_email_task
        job = q.enqueue(process_sent_email_task, session['credentials'], msg_id, job_timeout=900)
        return jsonify({
            'status': 'started',
            'job_id': job.get_id(),
            'message': 'Sent email analysis enqueued'
        }), 202
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_bp.route('/api/log_sent_email', methods=['POST'])
def log_sent_email():
    """
    Accepts sent email data and enqueues follow-up detection.
    Expected JSON: { msg_id, subject (optional), content (optional) }
    ---
    tags:
      - Follow-up
    security:
      - sessionAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - msg_id
          properties:
            msg_id:
              type: string
              description: Gmail message ID of sent email
            subject:
              type: string
              description: Email subject (optional)
            content:
              type: string
              description: Email content (optional)
    responses:
      202:
        description: Sent email logged and enqueued
        schema:
          type: object
          properties:
            status:
              type: string
              example: started
            job_id:
              type: string
            message:
              type: string
      400:
        description: Missing msg_id
      401:
        description: Not authorized
      500:
        description: Error enqueueing task
    """
    if 'credentials' not in session:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 401

    data = request.get_json() or {}
    msg_id = data.get('msg_id')
    if not msg_id:
        return jsonify({'status': 'error', 'message': 'Missing msg_id'}), 400

    subject = data.get('subject')
    content = data.get('content')

    try:
        redis_conn = Redis.from_url(REDIS_URL)
        redis_conn.ping()
        q = Queue(connection=redis_conn)
        
        from tasks.email_processing import process_sent_email_task
        job = q.enqueue(process_sent_email_task, session['credentials'], msg_id, subject, content, job_timeout=900)
        return jsonify({
            'status': 'started',
            'job_id': job.get_id(),
            'message': 'Sent email logged and enqueued for follow-up detection'
        }), 202
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_bp.route('/save-followup-credentials', methods=['POST'])
def save_followup_credentials():
    """
    Save current session credentials to file for scheduler.py.
    Requires authentication.
    ---
    tags:
      - Follow-up
    security:
      - sessionAuth: []
    responses:
      200:
        description: Credentials saved successfully
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
            path:
              type: string
              description: Path to saved credentials file
      400:
        description: No refresh_token found
      401:
        description: Not authenticated
      500:
        description: Error saving credentials
    """
    if 'credentials' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    try:
        from decouple import config as get_config
        followup_creds_path = get_config("FOLLOWUP_CREDENTIALS_PATH", default="followup_credentials.json")
        
        credentials_json = session['credentials']
        creds_dict = json.loads(credentials_json)
        
        if not creds_dict.get('refresh_token'):
            return jsonify({
                'status': 'error',
                'message': 'No refresh_token found. Please re-authorize with prompt=consent to get refresh_token.'
            }), 400
        
        with open(followup_creds_path, 'w', encoding='utf-8') as token_file:
            token_file.write(credentials_json)
        
        logger.info(f"Follow-up credentials saved to {followup_creds_path}")
        return jsonify({
            'status': 'success',
            'message': f'Credentials saved to {followup_creds_path}',
            'path': followup_creds_path
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error saving follow-up credentials: {error_details}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to save credentials: {str(e)}'
        }), 500

