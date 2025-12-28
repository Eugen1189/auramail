"""
Cache helper utilities for AuraMail.
Handles cache invalidation for dashboard and other cached endpoints.
"""
from flask import has_app_context, current_app


def invalidate_dashboard_cache():
    """
    Invalidates dashboard-related cache entries.
    Should be called when database changes occur that affect dashboard data.
    """
    try:
        if not has_app_context():
            return
        
        cache = getattr(current_app, 'cache', None)
        if cache is None:
            return
        
        # Invalidate dashboard index cache
        try:
            cache.delete('dashboard_index')
        except Exception:
            pass
        
        # Invalidate API progress cache
        try:
            cache.delete('api_progress')
        except Exception:
            pass
        
        # Invalidate report page cache
        try:
            cache.delete('report_page')
        except Exception:
            pass
    except Exception as e:
        # Silently handle any errors - cache invalidation should not break the flow
        print(f"⚠️ Error invalidating cache: {e}")
