# Caching Setup Guide for AuraMail

## Overview

AuraMail uses Flask-Caching with Redis for API response caching to improve performance:
- Dashboard statistics cached for 5 minutes
- Action history cached for 1 minute
- Progress API cached for 5 seconds
- Cache automatically invalidated when data changes

## Configuration

### 1. Redis Setup for Caching

Caching uses a separate Redis database (DB 1) from the task queue (DB 0):

```env
# In .env file
REDIS_URL=redis://localhost:6379/0          # For RQ task queue
CACHE_REDIS_URL=redis://localhost:6379/1    # For Flask-Caching
```

### 2. Cache Timeouts

Configure cache timeouts in `.env`:

```env
CACHE_DEFAULT_TIMEOUT=300                    # 5 minutes default
CACHE_DASHBOARD_STATS_TIMEOUT=300            # Dashboard cache (5 minutes)
CACHE_ACTION_HISTORY_TIMEOUT=60              # Action history cache (1 minute)
```

## How It Works

### Cached Endpoints

1. **Dashboard (`/`)** - Cached for 5 minutes
   - Statistics calculation
   - Recent activities
   - Daily stats

2. **Report Page (`/report`)** - Cached for 1 minute
   - Latest report
   - Recent actions
   - Log data

3. **Progress API (`/api/progress`)** - Cached for 5 seconds
   - Current processing progress
   - Short timeout because progress updates frequently

### Cache Invalidation

Cache is automatically invalidated when:
- New email action is logged (`log_action()`)
- New report is saved (`save_report()`)

This ensures users see fresh data after operations complete.

## Manual Cache Management

### Clear All Cache

```python
from server import cache
cache.clear()
```

### Clear Specific Cache

```python
from utils.cache_helper import invalidate_dashboard_cache
invalidate_dashboard_cache()
```

## Performance Benefits

- **Before caching**: Each dashboard load = 3-5 database queries
- **After caching**: First load = 3-5 queries, subsequent loads = 0 queries (from Redis)
- **Result**: 10-100x faster response times for cached endpoints

## Monitoring

Check cache hit rate in Redis:

```bash
redis-cli -n 1
> INFO stats
```

Look for `keyspace_hits` and `keyspace_misses` to calculate hit rate.

## Production Recommendations

1. **Use separate Redis instance** for cache in production (not just different DB)
2. **Monitor memory usage** - Redis cache can grow large
3. **Set maxmemory policy** in Redis config:
   ```
   maxmemory 256mb
   maxmemory-policy allkeys-lru
   ```
4. **Adjust timeouts** based on your usage patterns
5. **Use cache warming** for frequently accessed endpoints

## Troubleshooting

### Cache not working?

1. Check Redis connection:
   ```bash
   python check_redis.py
   ```

2. Verify cache is initialized:
   ```python
   from server import cache
   print(cache.config)
   ```

3. Check cache keys:
   ```bash
   redis-cli -n 1
   > KEYS *
   ```

### Cache not invalidating?

- Ensure `_invalidate_cache()` is called after data changes
- Check that cache helper is imported correctly
- Verify Redis connection is working


