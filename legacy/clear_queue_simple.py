"""Simple script to clear Redis queue - run this to fix run_task_in_context error"""
import redis
from rq import Queue
from rq.registry import FailedJobRegistry, StartedJobRegistry

# Connect to Redis
REDIS_URL = 'redis://localhost:6379/0'
conn = redis.from_url(REDIS_URL)

try:
    conn.ping()
    print("✅ Connected to Redis")
except Exception as e:
    print(f"❌ Cannot connect to Redis: {e}")
    print("Make sure Redis is running!")
    exit(1)

# Clear default queue
q = Queue('default', connection=conn)
job_count = len(q)
print(f"Found {job_count} jobs in queue")

if job_count > 0:
    print("Clearing queue...")
    q.empty()
    print("✅ Queue cleared!")
else:
    print("✅ Queue is already empty")

# Also clear failed jobs
failed = FailedJobRegistry('default', connection=conn)
failed_ids = failed.get_job_ids()
if failed_ids:
    print(f"Found {len(failed_ids)} failed jobs")
    for job_id in failed_ids:
        failed.remove(job_id)
    print("✅ Failed jobs cleared!")
else:
    print("✅ No failed jobs")

# Clear started jobs
started = StartedJobRegistry('default', connection=conn)
started_ids = started.get_job_ids()
if started_ids:
    print(f"Found {len(started_ids)} started jobs")
    for job_id in started_ids:
        started.remove(job_id)
    print("✅ Started jobs cleared!")
else:
    print("✅ No started jobs")

print("\n✅ All done! You can now restart your worker.")

