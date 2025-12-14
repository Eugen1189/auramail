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
from rq.worker import SimpleWorker

# Import app factory to create Flask app instance
from app_factory import create_app

# Налаштування
listen = ['default']
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = redis.from_url(redis_url)


if __name__ == '__main__':
    print("[Worker] Starting AuraMail Worker (Windows Simple Mode)...")
    print("[Worker] Initializing Flask app and database...")

    # Create Flask app instance - this will be used for all tasks
    app = create_app()
    
    # Initialize database within app context to ensure tables exist
    with app.app_context():
        from database import db
        # Ensure tables exist (creates them if they don't)
        db.create_all()
        print("[Worker] ✅ Database initialized successfully - tables verified")

    # Create queues
    queues = [Queue(name, connection=conn) for name in listen]

    # Wrap tasks with Flask app context
    # RQ Worker executes tasks in separate threads, so we need app context per task
    # Each task gets its own app context to ensure thread-safety
    from tasks import background_sort_task, voice_search_task
    
    # Store original functions before wrapping
    original_background_sort_task = background_sort_task
    original_voice_search_task = voice_search_task
    
    def wrapped_background_sort_task(*args, **kwargs):
        """
        Wrapper that ensures Flask app context is available for the task.
        Creates a new app instance per task to ensure clean state and thread-safety.
        """
        task_app = create_app()
        with task_app.app_context():
            return original_background_sort_task(*args, **kwargs)
    
    def wrapped_voice_search_task(*args, **kwargs):
        """
        Wrapper that ensures Flask app context is available for the task.
        Creates a new app instance per task to ensure clean state and thread-safety.
        """
        task_app = create_app()
        with task_app.app_context():
            return original_voice_search_task(*args, **kwargs)
    
    # Replace tasks in module with wrapped versions
    # This ensures all RQ task executions have proper Flask app context
    import tasks
    tasks.background_sort_task = wrapped_background_sort_task
    tasks.voice_search_task = wrapped_voice_search_task

    # Use SimpleWorker (without fork for Windows compatibility)
    # SimpleWorker runs tasks in threads, so app context from wrappers will work correctly
    # Note: We don't wrap worker.work() in app_context because each task creates its own
    worker = SimpleWorker(queues, connection=conn)
    print("[Worker] ✅ Worker started, waiting for tasks...")
    print("[Worker] Each task will have Flask app context with initialized database")
    worker.work()

