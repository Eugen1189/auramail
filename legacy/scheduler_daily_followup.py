import json
import os
import sys
from decouple import config
import redis
from rq import Queue

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from tasks import daily_followup_check

# Load configuration
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
FOLLOWUP_CREDENTIALS_PATH = config("FOLLOWUP_CREDENTIALS_PATH", default="followup_credentials.json")


def load_credentials_json(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Credentials file not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    # Validate JSON
    json.loads(data)
    return data


def main():
    # Load credentials JSON used specifically for scheduled follow-up checks
    credentials_json = load_credentials_json(FOLLOWUP_CREDENTIALS_PATH)

    # Enqueue daily follow-up check
    redis_conn = redis.from_url(REDIS_URL)
    redis_conn.ping()
    q = Queue(connection=redis_conn)
    job = q.enqueue(daily_followup_check, credentials_json)
    print(f"✅ Enqueued daily_followup_check job: {job.get_id()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Failed to enqueue daily follow-up check: {e}")
        sys.exit(1)






