import os
import redis
import sys

# Fix encoding for Windows console (handle Unicode characters)
if sys.platform == 'win32':
    try:
        # Set UTF-8 encoding for stdout/stderr on Windows
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass  # If reconfiguration fails, continue anyway

from rq import Queue
from rq.worker import SimpleWorker  # <--- Важливо: Імпортуємо SimpleWorker

# Налаштування
listen = ['default']
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = redis.from_url(redis_url)


if __name__ == '__main__':
    print("[Worker] Starting AuraMail Worker (Windows Simple Mode)...")

    # Створюємо черги з активним з'єднанням
    queues = [Queue(name, connection=conn) for name in listen]

    # Використовуємо SimpleWorker замість звичайного Worker (без fork)
    worker = SimpleWorker(queues, connection=conn)
    worker.work()

