#!/usr/bin/env python3
"""
Quick script to check Redis connection.
"""
import sys
import redis
from config import REDIS_URL
from redis import Redis

try:
    print(f"🔍 Перевірка підключення до Redis: {REDIS_URL}")
    redis_conn = Redis.from_url(REDIS_URL)
    redis_conn.ping()
    print("✅ Redis підключено успішно!")
    
    # Check if we can enqueue a test job
    from rq import Queue
    q = Queue(connection=redis_conn)
    print(f"✅ Черга 'default' доступна. Задач у черзі: {len(q)}")
    
except redis.ConnectionError as e:
    print(f"❌ Помилка підключення до Redis: {e}")
    print(f"\n💡 Рішення:")
    print(f"   1. Переконайтеся, що Redis запущений")
    print(f"   2. Перевірте REDIS_URL в .env файлі: {REDIS_URL}")
    print(f"   3. Для Windows: встановіть Redis або використайте Docker")
    sys.exit(1)
except Exception as e:
    print(f"❌ Помилка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
