"""
Cache helper functions for invalidating cache when data changes.
"""
from server import cache


def invalidate_dashboard_cache():
    """Invalidate dashboard cache after data changes."""
    try:
        cache.delete('dashboard_index')
        cache.delete('report_page')
        cache.delete('api_progress')
        print("✅ Cache invalidated: dashboard, report, progress")
    except Exception as e:
        print(f"⚠️ Cache invalidation error: {e}")


def invalidate_stats_cache():
    """Invalidate statistics cache."""
    try:
        cache.delete('dashboard_index')
        cache.delete('report_page')
        print("✅ Cache invalidated: stats")
    except Exception as e:
        print(f"⚠️ Cache invalidation error: {e}")








