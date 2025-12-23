"""
Redis Streams Logger for AuraMail.
Temporarily stores logs in Redis Streams during processing, then batch writes to database.

CRITICAL OPTIMIZATION: Instead of writing each log entry to SQLite during processing,
this module uses Redis Streams for temporary storage, then performs batch writes to DB
after task completion. This significantly reduces database I/O and improves performance.
"""
import json
import redis
from typing import List, Dict, Optional
from datetime import datetime
from config import CACHE_REDIS_URL
from utils.db_logger import log_action as db_log_action

# Redis connection for streams
_redis_client: Optional[redis.Redis] = None
STREAM_KEY_PREFIX = "auramail:logs:"


def get_redis_client() -> Optional[redis.Redis]:
    """
    Gets or creates Redis client for streams.
    
    Returns:
        Redis client instance or None if connection fails
    """
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(CACHE_REDIS_URL, decode_responses=True)
            # Test connection
            _redis_client.ping()
            print("✅ [Redis Logger] Connected to Redis for stream logging")
        except Exception as e:
            print(f"⚠️ [Redis Logger] Failed to connect to Redis: {e}")
            print("   Falling back to direct database logging")
            _redis_client = None
    return _redis_client


def log_to_stream(task_id: str, msg_id: str, classification: Dict, action_taken: str, subject: str):
    """
    Logs action to Redis Stream instead of database.
    
    CRITICAL OPTIMIZATION: Stores logs temporarily in Redis Streams during processing,
    then batch writes to database after task completion. This reduces database I/O.
    
    Args:
        task_id: Unique task identifier (e.g., timestamp or UUID)
        msg_id: Email message ID
        classification: Classification dictionary
        action_taken: Action performed
        subject: Email subject
    """
    client = get_redis_client()
    if not client:
        # Fallback to direct database logging if Redis unavailable
        db_log_action(msg_id, classification, action_taken, subject)
        return
    
    try:
        stream_key = f"{STREAM_KEY_PREFIX}{task_id}"
        
        log_entry = {
            'msg_id': msg_id,
            'classification': json.dumps(classification),
            'action_taken': action_taken,
            'subject': subject,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add to Redis Stream
        client.xadd(stream_key, log_entry)
        
    except Exception as e:
        print(f"⚠️ [Redis Logger] Failed to log to stream: {e}")
        # Fallback to direct database logging
        db_log_action(msg_id, classification, action_taken, subject)


def flush_stream_to_db(task_id: str) -> int:
    """
    Flushes all logs from Redis Stream to database in batch.
    
    CRITICAL OPTIMIZATION: Performs batch write of all logs from Redis Stream to database.
    This is much more efficient than individual writes during processing.
    
    Args:
        task_id: Task identifier for stream key
    
    Returns:
        Number of entries flushed
    """
    client = get_redis_client()
    if not client:
        return 0
    
    try:
        stream_key = f"{STREAM_KEY_PREFIX}{task_id}"
        
        # Read all entries from stream
        entries = client.xread({stream_key: '0'}, count=10000)
        
        if not entries:
            return 0
        
        flushed_count = 0
        for stream, messages in entries:
            for msg_id_stream, data in messages:
                try:
                    # Parse classification from JSON
                    classification = json.loads(data.get('classification', '{}'))
                    action_taken = data.get('action_taken', 'UNKNOWN')
                    subject = data.get('subject', '')
                    msg_id = data.get('msg_id', '')
                    
                    # Write to database
                    db_log_action(msg_id, classification, action_taken, subject)
                    flushed_count += 1
                    
                except Exception as e:
                    print(f"⚠️ [Redis Logger] Failed to flush entry {msg_id_stream}: {e}")
        
        # Delete stream after flushing
        try:
            client.delete(stream_key)
        except Exception:
            pass
        
        print(f"✅ [Redis Logger] Flushed {flushed_count} entries from stream to database")
        return flushed_count
        
    except Exception as e:
        print(f"⚠️ [Redis Logger] Failed to flush stream: {e}")
        return 0


def clear_stream(task_id: str):
    """
    Clears Redis Stream for a task (cleanup).
    
    Args:
        task_id: Task identifier for stream key
    """
    client = get_redis_client()
    if not client:
        return
    
    try:
        stream_key = f"{STREAM_KEY_PREFIX}{task_id}"
        client.delete(stream_key)
    except Exception:
        pass

