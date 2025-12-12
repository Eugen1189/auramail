"""
Database-based logger functions.
Replaces JSON file-based logging with SQLAlchemy models.
"""
from datetime import datetime, timedelta
from database import db, ActionLog, Progress, Report

# Import cache invalidation helper (lazy import to avoid circular dependency)
def _invalidate_cache():
    """Invalidate cache when data changes."""
    try:
        from utils.cache_helper import invalidate_stats_cache
        invalidate_stats_cache()
    except ImportError:
        pass  # Cache helper not available yet


def log_action(msg_id, classification, action_taken, subject):
    """
    Logs action to database.
    Replaces JSON file logging.
    """
    try:
        # Check if entry already exists (update instead of duplicate)
        existing = ActionLog.query.filter_by(msg_id=msg_id).first()
        
        entry = {
            'msg_id': msg_id,
            'subject': subject,
            'ai_category': classification.get('category', 'UNKNOWN'),
            'action_taken': action_taken,
            'reason': classification.get('description', ''),
            'details': classification
        }
        
        if existing:
            # Update existing entry
            existing.timestamp = datetime.utcnow()
            existing.subject = entry['subject']
            existing.ai_category = entry['ai_category']
            existing.action_taken = entry['action_taken']
            existing.reason = entry['reason']
            existing.details = entry['details']
        else:
            # Create new entry
            log_entry = ActionLog(**entry)
            db.session.add(log_entry)
        
        db.session.commit()
        # NOTE: Cache invalidation removed from here to avoid excessive calls
        # Cache will be invalidated once after all emails are processed (in save_report)
    except Exception as e:
        db.session.rollback()
        print(f"Error logging action to database: {e}")


def get_log_entry(msg_id):
    """
    Finds a specific log entry by message ID.
    Returns dictionary for compatibility with old JSON format.
    """
    try:
        entry = ActionLog.query.filter_by(msg_id=msg_id).first()
        return entry.to_dict() if entry else None
    except Exception:
        return None


def get_action_history(limit=50):
    """
    Returns recent actions.
    Returns list of dictionaries for compatibility with old JSON format.
    """
    try:
        entries = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(limit).all()
        return [entry.to_dict() for entry in reversed(entries)]  # Reverse to show oldest first
    except Exception:
        return []


def get_daily_stats(days=7):
    """
    Calculates stats for the last N days.
    Returns dictionary with date strings as keys.
    """
    stats = {}
    try:
        now = datetime.utcnow()
        for i in range(days):
            date_str = (now - timedelta(days=i)).strftime('%Y-%m-%d')
            stats[date_str] = 0
        
        # Query logs from last N days
        cutoff_date = now - timedelta(days=days)
        entries = ActionLog.query.filter(ActionLog.timestamp >= cutoff_date).all()
        
        for entry in entries:
            date_str = entry.timestamp.strftime('%Y-%m-%d')
            if date_str in stats:
                stats[date_str] += 1
                
        return stats
    except Exception:
        return stats


# --- PROGRESS TRACKING FUNCTIONS ---

def init_progress(total=0):
    """
    Initializes progress tracking in database.
    Replaces progress.json file.
    """
    try:
        # Get or create single progress record
        progress = Progress.query.first()
        if not progress:
            progress = Progress()
            db.session.add(progress)
        
        progress.total = total
        progress.current = 0
        progress.status = 'Starting...'
        progress.details = 'Initializing...'
        progress.stats = {}
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing progress: {e}")


def update_progress(current, stats=None, details=''):
    """
    Updates current progress in database.
    """
    try:
        progress = Progress.query.first()
        if not progress:
            init_progress()
            progress = Progress.query.first()
        
        progress.current = current
        progress.status = 'Processing...'
        
        if stats:
            progress.stats = stats
        if details:
            progress.details = details
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error updating progress: {e}")


def complete_progress(stats=None):
    """
    Marks process as complete in database.
    """
    try:
        progress = Progress.query.first()
        if not progress:
            init_progress()
            progress = Progress.query.first()
        
        progress.current = progress.total
        progress.status = 'Completed'
        progress.details = 'Done'
        
        if stats:
            progress.stats = stats
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error completing progress: {e}")


def get_progress():
    """
    Reads current progress from database.
    Returns dictionary for API compatibility.
    """
    try:
        progress = Progress.query.first()
        if progress:
            return progress.to_dict()
        else:
            # Return default if no progress record exists
            return {
                'total': 0,
                'current': 0,
                'status': 'Idle',
                'details': '',
                'stats': {},
                'progress_percentage': 0
            }
    except Exception:
        return {
            'total': 0,
            'current': 0,
            'status': 'Error',
            'details': '',
            'stats': {},
            'progress_percentage': 0
        }


# --- REPORT FUNCTIONS ---

def save_report(stats):
    """
    Saves sorting report to database.
    Replaces last_report.json file.
    
    Args:
        stats: Dictionary with statistics
    """
    try:
        report = Report(
            total_processed=stats.get('total_processed', 0),
            important=stats.get('important', 0),
            action_required=stats.get('action_required', 0),
            newsletter=stats.get('newsletter', 0),
            social=stats.get('social', 0),
            review=stats.get('review', 0),
            deleted=stats.get('deleted', 0),
            errors=stats.get('errors', 0),
            stats=stats
        )
        db.session.add(report)
        db.session.commit()
        # Invalidate cache when new report is saved
        _invalidate_cache()
    except Exception as e:
        db.session.rollback()
        print(f"Error saving report: {e}")


def get_latest_report():
    """
    Gets the latest sorting report from database.
    Returns dictionary for compatibility with old JSON format.
    """
    try:
        report = Report.query.order_by(Report.created_at.desc()).first()
        if report:
            return report.to_dict()
        else:
            # Return empty stats if no report exists
            return {
                'total_processed': 0,
                'important': 0,
                'action_required': 0,
                'newsletter': 0,
                'social': 0,
                'review': 0,
                'deleted': 0,
                'errors': 0
            }
    except Exception:
        return {
            'total_processed': 0,
            'important': 0,
            'action_required': 0,
            'newsletter': 0,
            'social': 0,
            'review': 0,
            'deleted': 0,
            'errors': 0
        }

