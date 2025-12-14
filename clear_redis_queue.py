#!/usr/bin/env python3
"""
Script to clear Redis queue from old jobs referencing deleted functions.
"""
import redis
import os
from rq import Queue
from config import REDIS_URL

def clear_queues():
    """Clear all jobs from RQ queues."""
    print("🔄 Connecting to Redis...")
    conn = redis.from_url(REDIS_URL)
    
    try:
        conn.ping()
        print(f"✅ Connected to Redis at {REDIS_URL}")
    except redis.ConnectionError as e:
        print(f"❌ Cannot connect to Redis: {e}")
        print("Make sure Redis is running!")
        return
    
    # Clear all queues
    queue_names = ['default', 'high', 'low']  # Common queue names
    
    for queue_name in queue_names:
        q = Queue(queue_name, connection=conn)
        job_count = len(q)
        
        if job_count > 0:
            print(f"🧹 Clearing {job_count} jobs from queue '{queue_name}'...")
            q.empty()
            print(f"✅ Cleared queue '{queue_name}'")
        else:
            print(f"✅ Queue '{queue_name}' is already empty")
    
    # Also clear failed and started job registries
    from rq.registry import StartedJobRegistry, FailedJobRegistry
    
    for queue_name in queue_names:
        q = Queue(queue_name, connection=conn)
        
        # Clear started jobs
        started = StartedJobRegistry(queue=q)
        started_ids = started.get_job_ids()
        if started_ids:
            print(f"🧹 Clearing {len(started_ids)} started jobs from '{queue_name}'...")
            for job_id in started_ids:
                started.remove(job_id)
            print(f"✅ Cleared started jobs from '{queue_name}'")
        
        # Clear failed jobs (optional - comment out if you want to keep them for debugging)
        failed = FailedJobRegistry(queue=q)
        failed_ids = failed.get_job_ids()
        if failed_ids:
            print(f"🧹 Found {len(failed_ids)} failed jobs in '{queue_name}'")
            print("   (Keeping failed jobs for debugging - uncomment code to clear them)")
            # Uncomment to clear failed jobs:
            # for job_id in failed_ids:
            #     failed.remove(job_id)
            # print(f"✅ Cleared failed jobs from '{queue_name}'")
    
    print("\n✅ Redis queue cleanup completed!")
    print("⚠️  You can now restart your worker and enqueue new jobs.")

if __name__ == '__main__':
    clear_queues()

