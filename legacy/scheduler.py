"""
Daily scheduler for AuraMail Follow-up Monitor.
Enqueues daily_followup_check task to RQ queue.

Usage:
    python scheduler.py

For production:
    - Set up Windows Task Scheduler (Windows) or Cron (Linux) to run daily
    - Ensure FOLLOWUP_CREDENTIALS_PATH points to valid credentials JSON file
    - Or implement get_persisted_credentials() to load from database
"""
import os
import sys
import json
import redis
from datetime import datetime, timedelta
from decouple import config
from rq import Queue

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import configuration and task
from config import REDIS_URL, SCOPES
from tasks import daily_followup_check

# Configuration for credentials path
FOLLOWUP_CREDENTIALS_PATH = config("FOLLOWUP_CREDENTIALS_PATH", default="followup_credentials.json")


def get_persisted_credentials():
    """
    Retrieves long-lived credentials for scheduled follow-up checks.
    
    Priority:
    1. Load from file (FOLLOWUP_CREDENTIALS_PATH) - recommended for simple setups
    2. Load from database (if implemented) - for production with multiple users
    3. Return placeholder (will fail gracefully)
    
    Returns:
        str: JSON string with OAuth credentials, or None if not available
    """
    # Option 1: Load from file (simple approach)
    if os.path.exists(FOLLOWUP_CREDENTIALS_PATH):
        try:
            with open(FOLLOWUP_CREDENTIALS_PATH, 'r', encoding='utf-8') as f:
                credentials_data = f.read()
            # Validate JSON and check for refresh_token
            creds_dict = json.loads(credentials_data)
            
            # Check for refresh_token (critical for scheduled tasks)
            if not creds_dict.get('refresh_token'):
                print(f"⚠️ WARNING: No refresh_token in {FOLLOWUP_CREDENTIALS_PATH}")
                print("   Credentials may expire and scheduler will stop working.")
                print("   Re-authorize via /authorize with prompt=consent to get refresh_token.")
                print("   Then save credentials via POST /save-followup-credentials")
            else:
                print(f"✅ Loaded credentials from {FOLLOWUP_CREDENTIALS_PATH}")
                print(f"   Refresh token present - credentials can auto-refresh")
            
            return credentials_data
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in {FOLLOWUP_CREDENTIALS_PATH}: {e}")
            print("   Please re-create the file via POST /save-followup-credentials")
        except Exception as e:
            print(f"⚠️ Error loading credentials from file: {e}")
    
    # Option 2: Load from database (for production with multiple users)
    # TODO: Implement database lookup for persisted credentials
    # Example:
    # from app_factory import create_app
    # from database import db
    # app = create_app()
    # with app.app_context():
    #     # Query database for active user credentials
    #     # Return credentials JSON string
    #     pass
    
    # Option 3: Placeholder (will fail gracefully)
    print("⚠️ No credentials found. Please set FOLLOWUP_CREDENTIALS_PATH or implement database lookup.")
    return None


def enqueue_daily_check():
    """
    Enqueues the daily_followup_check task to RQ queue.
    
    Uses unique job_id per day to prevent duplicate jobs.
    Sets TTL to prevent jobs from hanging indefinitely.
    """
    try:
        # 1. Get credentials (required for Gmail API in task)
        credentials_json = get_persisted_credentials()
        
        if not credentials_json:
            print("❌ Error: Cannot run daily check without valid credentials.")
            print(f"   Please create {FOLLOWUP_CREDENTIALS_PATH} with valid OAuth credentials JSON.")
            print("   Or implement get_persisted_credentials() to load from database.")
            return False
        
        # 2. Connect to Redis
        try:
            redis_conn = redis.from_url(REDIS_URL)
            redis_conn.ping()
        except redis.ConnectionError as e:
            print(f"❌ Redis connection error: {e}")
            print(f"   Make sure Redis is running on {REDIS_URL}")
            return False
        
        # 3. Create queue and enqueue task
        q = Queue('default', connection=redis_conn)
        
        # Generate unique job ID per day to prevent duplicates
        job_id = f'daily-followup-check-{datetime.now().strftime("%Y%m%d")}'
        
        # Check if job already exists (prevent duplicate runs on same day)
        try:
            existing_job = q.fetch_job(job_id)
            if existing_job and existing_job.get_status() in ('queued', 'started'):
                print(f"⚠️ Job {job_id} already exists and is {existing_job.get_status()}. Skipping.")
                return False
        except Exception:
            # Job doesn't exist, continue
            pass
        
        # Enqueue task with priority and TTL
        # Set timeout to 15 minutes (900 seconds) for long-running tasks (Gemini API, Gmail API)
        job = q.enqueue(
            daily_followup_check,
            credentials_json,
            job_id=job_id,
            at_front=True,  # High priority
            ttl=timedelta(days=1).total_seconds(),  # TTL: 24 hours
            job_timeout=900  # Timeout: 15 minutes for long-running operations
        )
        
        print(f"✅ Daily follow-up check enqueued successfully.")
        print(f"   Job ID: {job.id}")
        print(f"   Queue: default")
        print(f"   TTL: 24 hours")
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection error: {e}")
        print(f"   Make sure Redis is running on {REDIS_URL}")
        return False
    except Exception as e:
        print(f"❌ General error during scheduling: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scheduler...")
    print(f"Redis URL: {REDIS_URL}")
    print(f"Credentials path: {FOLLOWUP_CREDENTIALS_PATH}")
    print("-" * 60)
    
    success = enqueue_daily_check()
    
    print("-" * 60)
    if success:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler completed successfully.")
        sys.exit(0)
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler failed.")
        sys.exit(1)

