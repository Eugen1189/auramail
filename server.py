"""
Flask application for AuraMail.
Contains only Flask routes, authentication, and server startup.
"""
import os
import sys
import json
from flask import redirect, url_for, session, request, render_template, flash, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from redis import Redis
import redis
from rq import Queue
from tasks import background_sort_task, voice_search_task  # Імпортуємо задачі для RQ

# Fix encoding for Windows console (handle Unicode characters)
if sys.platform == 'win32':
    try:
        # Set UTF-8 encoding for stdout/stderr on Windows
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass  # If reconfiguration fails, continue anyway

# Import configuration
from config import (
    CLIENT_SECRETS_FILE,
    SCOPES,
    BASE_URI,
    FLASK_SECRET_KEY,
    REDIS_URL,
    CORS_ORIGINS,
    ALLOW_ALL_CORS,
    FORCE_HTTPS,
    DEBUG,
    CACHE_REDIS_URL,
    CACHE_DEFAULT_TIMEOUT,
    CACHE_DASHBOARD_STATS_TIMEOUT,
    CACHE_ACTION_HISTORY_TIMEOUT
)

# Import utility modules
from utils.gmail_api import build_google_services, rollback_action
from utils.db_logger import (
    get_log_entry,
    get_action_history,
    get_daily_stats,
    get_progress,
    get_latest_report
)

# Import database
from database import db

# Import app factory
from app_factory import create_app

# Import monitoring and logging
from utils.monitoring import metrics_endpoint, track_api_request
from utils.logging_config import get_logger

# Create Flask application using factory
app = create_app()

# Ensure cache is properly configured for testing
# app_factory should have already set CACHE_TYPE='NullCache' if TESTING=True
# This is a safety check to ensure cache configuration is correct
if app.config.get('TESTING', False) and app.config.get('CACHE_TYPE') != 'NullCache':
    # Reconfigure cache to NullCache if not already set
    app.config['CACHE_TYPE'] = 'NullCache'
    app.cache.init_app(app, config={
        'CACHE_TYPE': 'NullCache',
        'CACHE_NO_NULL_WARNING': True
    })

# Get cache instance from app
cache = app.cache

# Initialize structured logging
logger = get_logger(__name__)
app_logger = get_logger(__name__)


# CORS and Talisman are configured in app_factory.create_app()
# Cache is configured in app_factory.create_app() with NullCache for testing


# --- HELPER FUNCTIONS ---
def create_flow():
    """
    Creates new Flow object for each request.
    Uses BASE_URI from config to form redirect_uri.
    """
    redirect_uri = f"{BASE_URI.rstrip('/')}/callback"
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )


def get_user_credentials():
    """Get credentials from session."""
    if 'credentials' not in session:
        return None
    credentials_json = session['credentials']
    return Credentials.from_authorized_user_info(json.loads(credentials_json), SCOPES)


def calculate_stats():
    """Calculate statistics from action history."""
    all_actions = get_action_history(limit=1000)
    return {
        'total_processed': len(all_actions),
        'important': sum(1 for a in all_actions if a.get('ai_category') == 'IMPORTANT'),
        'review': sum(1 for a in all_actions if a.get('ai_category') == 'REVIEW'),
        'archived': sum(1 for a in all_actions if a.get('action_taken') == 'ARCHIVE'),
        'action_required': sum(1 for a in all_actions if a.get('ai_category') == 'ACTION_REQUIRED'),
        'newsletter': sum(1 for a in all_actions if a.get('ai_category') == 'NEWSLETTER'),
        'social': sum(1 for a in all_actions if a.get('ai_category') == 'SOCIAL'),
        'errors': sum(1 for a in all_actions if a.get('status', '').startswith('ERROR'))
    }


def get_empty_stats():
    """Return empty statistics dictionary."""
    return {
        'total_processed': 0,
        'important': 0,
        'action_required': 0,
        'newsletter': 0,
        'social': 0,
        'review': 0,
        'archived': 0,
        'errors': 0
    }


def build_label_cache(service):
    """Build label cache from Gmail service."""
    label_cache = {}
    try:
        response = service.users().labels().list(userId='me').execute()
        for label in response.get('labels', []):
            label_cache[label['name']] = label['id']
    except Exception:
        pass  # Return empty cache if fails
    return label_cache


# --- 1. AUTHENTICATION ROUTE ---
@app.route('/authorize')
def authorize():
    """Redirect user to Google OAuth authorization page."""
    try:
        # Make session permanent before saving state
        # This ensures session persists during OAuth redirect
        session.permanent = True
        
        flow = create_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        session['oauth_state'] = state
        return redirect(authorization_url)
    except Exception as e:
        import traceback
        return f'<h1>❌ Помилка при авторизації</h1><p>Деталі: {str(e)}</p><pre>{traceback.format_exc()}</pre><p><a href="/">Повернутися на головну</a></p>', 500


# --- 2. TOKEN PROCESSING ROUTE ---
@app.route('/callback')
def callback():
    """Process OAuth callback and save credentials."""
    try:
        # Check for error in request parameters
        error = request.args.get('error')
        if error:
            error_description = request.args.get('error_description', 'Невідома помилка')
            return f'<h1>❌ Помилка OAuth</h1><p><strong>Помилка:</strong> {error}</p><p><strong>Опис:</strong> {error_description}</p><p><a href="/authorize">Спробувати знову</a></p>', 400
        
        # Check state for CSRF protection
        state = request.args.get('state')
        if 'oauth_state' not in session or state != session.get('oauth_state'):
            return '<h1>❌ Помилка безпеки</h1><p>State параметр не збігається. Будь ласка, <a href="/authorize">спробуйте знову</a>.</p>', 400
        
        # Process return from Google and save token
        flow = create_flow()
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Make session permanent before saving credentials
        # This ensures session persists across requests
        session.permanent = True
        
        # Save token in session
        session['credentials'] = credentials.to_json()
        
        # Verify scopes are granted
        if credentials.scopes:
            granted_set = set(credentials.scopes)
            required_set = set(SCOPES)
            if not required_set.issubset(granted_set):
                missing = required_set - granted_set
                flash(f"⚠️ Попередження: Відсутні дозволи: {', '.join(sorted(missing))}", 'warning')
        
        # Remove state after successful authorization
        session.pop('oauth_state', None)
        return redirect(url_for('index'))
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f'<h1>❌ Помилка при обробці токена</h1><p>Деталі: {str(e)}</p><pre>{error_details}</pre><p><a href="/">Повернутися на головну</a></p>', 500


# --- 3. MAIN ROUTE (Home page) ---
@app.route('/')
@cache.cached(timeout=CACHE_DASHBOARD_STATS_TIMEOUT, key_prefix='dashboard_index')
def index():
    if 'credentials' not in session:
        return render_template('login.html')
    
    # User is authenticated, show dashboard
    try:
        creds = get_user_credentials()
        service, _ = build_google_services(creds)
        
        # Get user profile to extract email
        profile = service.users().getProfile(userId='me').execute()
        user_email = profile.get('emailAddress', 'Unknown')
        
        # Get recent activities (last 10)
        recent_activities = get_action_history(limit=10)
        recent_activities.reverse()  # Show newest first
        
        # Calculate stats from log
        stats = calculate_stats()
        
        # Get daily stats for last 7 days
        daily_stats = get_daily_stats(days=7)
        
        return render_template('dashboard.html', 
                             user_email=user_email,
                             recent_activities=recent_activities,
                             stats=stats,
                             daily_stats=daily_stats)
    except Exception as e:
        # Fallback if there's an error
        return f'<h1>❌ Помилка</h1><p>Деталі: {str(e)}</p><p><a href="/">Повернутися на головну</a></p>', 500


# --- 4. ОНОВЛЕНИЙ МАРШРУТ ЗАПУСКУ (тепер миттєвий) ---
@app.route('/sort')
def start_sort_job():
    if 'credentials' not in session:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 401
    
    try:
        # Підключаємось до Redis
        redis_conn = Redis.from_url(REDIS_URL)
        
        # Test connection
        redis_conn.ping()
        
        q = Queue(connection=redis_conn)
        
        # Ставимо задачу в чергу напряму
        # Worker will create Flask app context automatically via wrapper
        job = q.enqueue(background_sort_task, session['credentials'])
        
        return jsonify({
            'status': 'started', 
            'job_id': job.get_id(),
            'message': 'Job enqueued successfully'
        })
    except redis.ConnectionError as e:
        import traceback
        error_msg = f"Redis connection error: {str(e)}. Make sure Redis is running on {REDIS_URL}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return jsonify({
            'status': 'error', 
            'message': error_msg
        }), 500
    except Exception as e:
        import traceback
        error_msg = f"Error starting job: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': error_msg}), 500


# --- 4b. НОВИЙ МАРШРУТ ДЛЯ ЗВІТУ ---
@app.route('/report')
@cache.cached(timeout=CACHE_ACTION_HISTORY_TIMEOUT, key_prefix='report_page')
def show_report():
    # Завантажуємо статистику з бази даних
    try:
        stats = get_latest_report()
            
        recent_actions = get_action_history(limit=20)
        log_data = get_action_history(limit=100)
        
        from config import is_production_ready
        
        return render_template('report.html', 
                             stats=stats, 
                             recent_actions=recent_actions, 
                             log_data=log_data,
                             is_prod_secure=is_production_ready())
    except Exception as e:
        return f'<h1>❌ Помилка звіту</h1><p>{str(e)}</p><p><a href="/">Повернутися на головну</a></p>', 500


# --- 5. PROGRESS API ENDPOINT (NEW) ---
@app.route('/api/progress')
@cache.cached(timeout=5, key_prefix='api_progress')  # Cache for 5 seconds (progress updates frequently)
def api_progress():
    """Returns current processing progress as JSON."""
    try:
        progress_data = get_progress()
        if progress_data is None:
            return jsonify({'error': 'No progress data available'}), 404
        return jsonify(progress_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- 6. ROLLBACK ROUTE ---
@app.route('/rollback/<string:msg_id>', methods=['POST'])
def rollback(msg_id):
    """Rollback action for a specific email message."""
    if 'credentials' not in session:
        flash("Помилка: потрібна авторизація.", 'danger')
        return redirect(url_for('authorize'))
    
    try:
        # 1. Initialize Gmail service and label cache
        creds = get_user_credentials()
        if not creds:
            flash("Помилка: потрібна авторизація.", 'danger')
            return redirect(url_for('authorize'))
        
        gmail_service, _ = build_google_services(creds)
        
        # Initialize label cache
        label_cache = build_label_cache(gmail_service)
        if not label_cache:
            flash("Помилка: не вдалося завантажити кеш міток.", 'danger')
            return redirect(url_for('show_report'))
        
        # 2. Find log entry
        log_entry = get_log_entry(msg_id)
        if not log_entry:
            flash("Помилка: запис про дію для цього листа не знайдено в журналі.", 'warning')
            return redirect(url_for('show_report'))
        
        # 3. Execute rollback
        status = rollback_action(gmail_service, log_entry, label_cache)
        
        if "ERROR" in status:
            flash(f"Помилка відкату: {status} (Не можна відмінити DELETE).", 'danger')
        elif "INFO" in status:
            flash(f"Інформація: {status}", 'info')
        else:
            flash(f"Відкат успішний: {status}.", 'success')
        
        # Invalidate cache after rollback
        from utils.cache_helper import invalidate_stats_cache
        invalidate_stats_cache()
        
        return redirect(url_for('show_report'))
        
    except Exception as e:
        flash(f"Помилка при виконанні відкату: {str(e)}", 'danger')
        return redirect(url_for('show_report'))


# --- 7. LOGOUT ROUTE ---
@app.route('/logout')
def logout():
    """Logout user by clearing session."""
    session.clear()
    flash("Ви успішно вийшли з системи. Credentials очищено.", 'info')
    return redirect(url_for('index'))


# --- 8. CLEAR CREDENTIALS ROUTE (for fixing OAuth scopes) ---
@app.route('/clear-credentials')
def clear_credentials():
    """Clear OAuth credentials from session. Use this if you get 'insufficient authentication scopes' error."""
    session.clear()
    app_logger.info("credentials_cleared", action="clear_credentials")
    flash("Credentials очищено. Будь ласка, авторизуйтеся знову з правильними дозволами.", 'warning')
    return redirect(url_for('authorize'))


# --- 9. PROMETHEUS METRICS ENDPOINT ---
@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint."""
    return metrics_endpoint()


# --- VOICE SEARCH ENDPOINT ---
@app.route('/voice/search', methods=['POST'])
def handle_voice_search():
    """Handle voice search request and enqueue task to RQ."""
    if 'credentials' not in session:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 401
    
    try:
        # Get search query from request
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'status': 'error', 'message': 'Missing query parameter'}), 400
        
        search_text = data.get('query', '').strip()
        if not search_text:
            return jsonify({'status': 'error', 'message': 'Query cannot be empty'}), 400
        
        # Connect to Redis
        redis_conn = Redis.from_url(REDIS_URL)
        redis_conn.ping()
        
        q = Queue(connection=redis_conn)
        
        # Enqueue voice search task напряму
        # Worker will create Flask app context automatically via wrapper
        job = q.enqueue(voice_search_task, session['credentials'], search_text)
        
        return jsonify({
            'status': 'started',
            'job_id': job.get_id(),
            'message': 'Voice search task enqueued successfully'
        }), 202
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [Voice Search] Error enqueueing task: {error_msg}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to start voice search: {error_msg}'
        }), 500


# Add middleware to track API requests and ensure session is permanent
@app.before_request
def before_request():
    """Track API request start time and ensure session is permanent."""
    from flask import g
    import time
    g.start_time = time.time()
    
    # Ensure session is permanent for all requests
    # This is critical for OAuth callback to work correctly
    session.permanent = True


@app.after_request
def after_request(response):
    """Track API request metrics after response."""
    from flask import g, request
    import time
    
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        track_api_request(
            endpoint=request.endpoint or request.path,
            method=request.method,
            status_code=response.status_code,
            duration=duration
        )
        
        # Log request
        app_logger.info(
            "api_request",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration=duration
        )
    
    return response


if __name__ == '__main__':
    # Rename your downloaded key file to 'client_secret.json'
    # and place it in the project folder.
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"Помилка: Файл '{CLIENT_SECRETS_FILE}' не знайдено.")
        print("Переконайтеся, що ви перейменували свій файл Google Cloud.")
    else:
        # Check JSON file validity
        try:
            with open(CLIENT_SECRETS_FILE, 'r', encoding='utf-8') as f:
                json.load(f)
            print("✅ client_secret.json валідний")
        except json.JSONDecodeError as e:
            print(f"❌ Помилка: client_secret.json містить невалідний JSON: {e}")
            print("Переконайтеся, що файл не містить коментарів або синтаксичних помилок.")
            exit(1)
        except Exception as e:
            print(f"❌ Помилка при читанні client_secret.json: {e}")
            exit(1)
        
        # Check for pyOpenSSL for SSL (only in development)
        if DEBUG:
            try:
                import OpenSSL
                print("✅ pyOpenSSL встановлено. Запускаємо сервер з HTTPS (dev mode)...")
                print("🌐 Сервер запускається на: https://127.0.0.1:5000")
                print("⚠️  Це режим розробки! Для продакшену використовуйте Gunicorn + Nginx")
                # Flask runs on port 5000 (development only)
                app.run(host='127.0.0.1', port=5000, ssl_context='adhoc', debug=DEBUG)
            except ImportError:
                print("❌ Помилка: pyOpenSSL не встановлено!")
                print("Встановіть його командою: pip install pyopenssl")
                print("\nАбо запустіть без SSL (не рекомендується для OAuth):")
                print("Закоментуйте рядок з ssl_context='adhoc' та використайте app.run(host='127.0.0.1', port=5000)")
        else:
            # Production mode - but allow running with warning for development/testing
            print("⚠️  Production mode (DEBUG=False) detected!")
            print("⚠️  Flask dev server is NOT recommended for production!")
            print("   For production, use: gunicorn -w 4 -b 0.0.0.0:5000 server:app")
            print("\n   Starting dev server anyway for development/testing...")
            print("   🌐 Server will run on: https://127.0.0.1:5000")
            
            # Still use adhoc SSL for OAuth to work
            try:
                import OpenSSL
                app.run(host='127.0.0.1', port=5000, ssl_context='adhoc', debug=False)
            except ImportError:
                print("❌ Помилка: pyOpenSSL не встановлено!")
                print("Встановіть його командою: pip install pyopenssl")
            # Alternative without SSL (won't work with OAuth, but for testing):
            # app.run(host='127.0.0.1', port=5000)
