"""
Database logging utilities for AuraMail.
Handles logging actions to database and retrieving logs.
"""
from datetime import datetime
from flask import has_app_context, current_app
from app_factory import create_app

from database import db, ActionLog, Progress, Report


def log_action(msg_id, classification, action_taken, subject):
    """
    Logs email processing action to database.
    
    Args:
        msg_id: Gmail message ID
        classification: Classification dictionary with category, description, etc.
        action_taken: Action that was taken (MOVE, ARCHIVE, NO_ACTION)
        subject: Email subject
    """
    try:
        # Ensure Flask app context
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _log_action_impl(msg_id, classification, action_taken, subject)
        else:
            return _log_action_impl(msg_id, classification, action_taken, subject)
    except Exception as e:
        print(f"⚠️ Error logging action: {e}")
        return None


def _log_action_impl(msg_id, classification, action_taken, subject):
    """Internal implementation of log_action (assumes context exists)."""
    try:
        # Extract classification data
        category = classification.get('category', 'UNKNOWN') if isinstance(classification, dict) else 'UNKNOWN'
        description = classification.get('description', '') if isinstance(classification, dict) else ''
        extracted_entities = classification.get('extracted_entities', {}) if isinstance(classification, dict) else {}
        
        # Extract follow-up data if present
        expected_reply_date = None
        if isinstance(extracted_entities, dict) and 'due_date' in extracted_entities:
            try:
                expected_reply_date = datetime.strptime(extracted_entities['due_date'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        
        # Check if entry already exists
        existing = ActionLog.query.filter_by(msg_id=msg_id).first()
        
        if existing:
            # Update existing entry
            existing.timestamp = datetime.utcnow()
            existing.subject = subject
            existing.ai_category = category
            existing.action_taken = action_taken
            existing.reason = description
            existing.details = classification
            existing.is_followup_pending = expected_reply_date is not None
            existing.expected_reply_date = expected_reply_date
        else:
            # Create new entry
            new_log = ActionLog(
                msg_id=msg_id,
                subject=subject,
                ai_category=category,
                action_taken=action_taken,
                reason=description,
                details=classification,
                is_followup_pending=expected_reply_date is not None,
                expected_reply_date=expected_reply_date
            )
            db.session.add(new_log)
        
        db.session.commit()
        return True
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f"⚠️ Error logging action: {e}")
        return False


def log_user_action(user_id, action_type, details=None):
    """
    Записує дію користувача в лог (тимчасова заглушка або реалізація).
    
    Args:
        user_id: ID користувача
        action_type: Тип дії
        details: Додаткові деталі (опціонально)
    """
    try:
        # Тут можна додати запис в БД, якщо у вас є модель UserLog
        # Але щоб система запрацювала прямо зараз, просто виведемо в консоль:
        print(f"📝 [ACTION LOG] User: {user_id} | Action: {action_type} | {details}")
    except Exception as e:
        print(f"⚠️ Error logging user action: {e}")


# Alias for backward compatibility if needed
def log_action(user_id=None, action_type=None, details=None, msg_id=None, classification=None, action_taken=None, subject=None):
    """
    Universal log_action function that handles both email actions and user actions.
    
    If msg_id is provided, logs email action (old signature).
    If user_id is provided, logs user action (new signature).
    """
    if msg_id is not None:
        # Email action logging (original signature)
        return log_action(msg_id, classification, action_taken, subject)
    elif user_id is not None:
        # User action logging (new signature)
        return log_user_action(user_id, action_type, details)
    else:
        print("⚠️ log_action called without required parameters")
        return None


def init_progress(total=0):
    """
    Initializes progress tracking in database.
    Deletes old progress entries and creates a new one.
    """
    try:
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _init_progress_impl(total)
        else:
            return _init_progress_impl(total)
    except Exception as e:
        print(f"⚠️ Error initializing progress: {e}")
        return None


def _init_progress_impl(total=0):
    """Internal implementation of init_progress (assumes context exists)."""
    try:
        Progress.query.delete()
        new_progress = Progress(total=total, current=0, status='Starting...', details='Initializing...', stats={})
        db.session.add(new_progress)
        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f"⚠️ Error initializing progress: {e}")


def update_progress(current, stats=None, details=''):
    """
    Updates progress tracking in database.
    
    Args:
        current: Current progress count
        stats: Statistics dictionary (optional)
        details: Progress details string (optional)
    """
    try:
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _update_progress_impl(current, stats, details)
        else:
            return _update_progress_impl(current, stats, details)
    except Exception as e:
        print(f"⚠️ Error updating progress: {e}")
        return None


def _update_progress_impl(current, stats=None, details=''):
    """Internal implementation of update_progress (assumes context exists)."""
    try:
        progress = Progress.query.first()
        if progress:
            progress.current = current
            progress.status = details or progress.status
            if stats:
                progress.stats = stats
            db.session.commit()
        else:
            # Create new progress if none exists
            new_progress = Progress(total=current, current=current, status=details, stats=stats or {})
            db.session.add(new_progress)
            db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f"⚠️ Error updating progress: {e}")


def complete_progress(stats=None):
    """
    Marks progress as complete in database.
    
    Args:
        stats: Final statistics dictionary (optional)
    """
    try:
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _complete_progress_impl(stats)
        else:
            return _complete_progress_impl(stats)
    except Exception as e:
        print(f"⚠️ Error completing progress: {e}")
        return None


def _complete_progress_impl(stats=None):
    """Internal implementation of complete_progress (assumes context exists)."""
    try:
        progress = Progress.query.first()
        if progress:
            progress.status = 'Completed'
            if stats:
                progress.stats = stats
            db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f"⚠️ Error completing progress: {e}")


def save_report(report_data):
    """
    Saves processing report to database.
    
    Args:
        report_data: Dictionary with report data
    """
    try:
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _save_report_impl(report_data)
        else:
            return _save_report_impl(report_data)
    except Exception as e:
        print(f"⚠️ Error saving report: {e}")
        return None


def _save_report_impl(report_data):
    """Internal implementation of save_report (assumes context exists)."""
    try:
        new_report = Report(
            timestamp=datetime.utcnow(),
            total_processed=report_data.get('total', 0),
            stats=report_data.get('stats', {}),
            details=report_data.get('details', {})
        )
        db.session.add(new_report)
        db.session.commit()
        return new_report.id
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f"⚠️ Error saving report: {e}")
        return None


def get_log_entry(msg_id):
    """
    Gets a specific log entry by message ID.
    
    Args:
        msg_id: Gmail message ID
        
    Returns:
        ActionLog object or None
    """
    try:
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _get_log_entry_impl(msg_id)
        else:
            return _get_log_entry_impl(msg_id)
    except Exception as e:
        print(f"⚠️ Error getting log entry: {e}")
        return None


def _get_log_entry_impl(msg_id):
    """Internal implementation of get_log_entry (assumes context exists)."""
    try:
        return ActionLog.query.filter_by(msg_id=msg_id).first()
    except Exception as e:
        print(f"⚠️ Error getting log entry: {e}")
        return None


def get_action_history(limit=50):
    """
    Gets recent action history from database.
    
    Args:
        limit: Maximum number of entries to return
        
    Returns:
        List of ActionLog objects
    """
    try:
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _get_action_history_impl(limit)
        else:
            return _get_action_history_impl(limit)
    except Exception as e:
        print(f"⚠️ Error getting action history: {e}")
        return []


def _get_action_history_impl(limit=50):
    """Internal implementation of get_action_history (assumes context exists)."""
    try:
        return ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(limit).all()
    except Exception as e:
        print(f"⚠️ Error getting action history: {e}")
        return []


def get_daily_stats(days=7):
    """
    Calculates daily statistics for the last N days.
    
    Args:
        days: Number of days to calculate stats for
        
    Returns:
        Dictionary with date strings as keys and counts as values
    """
    try:
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _get_daily_stats_impl(days)
        else:
            return _get_daily_stats_impl(days)
    except Exception as e:
        print(f"⚠️ Error getting daily stats: {e}")
        return {}


def _get_daily_stats_impl(days=7):
    """Internal implementation of get_daily_stats (assumes context exists)."""
    try:
        from datetime import timedelta
        
        stats = {}
        now = datetime.utcnow()
        
        # Initialize dates
        for i in range(days):
            date_str = (now - timedelta(days=i)).date().isoformat()
            stats[date_str] = 0
        
        # Count actions per day
        cutoff_date = now - timedelta(days=days)
        actions = ActionLog.query.filter(ActionLog.timestamp >= cutoff_date).all()
        
        for action in actions:
            date_str = action.timestamp.date().isoformat()
            if date_str in stats:
                stats[date_str] += 1
        
        return stats
    except Exception as e:
        print(f"⚠️ Error getting daily stats: {e}")
        return {}


def get_progress():
    """
    Gets current progress from database.
    
    Returns:
        Dictionary with progress data or None
    """
    try:
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _get_progress_impl()
        else:
            return _get_progress_impl()
    except Exception as e:
        print(f"⚠️ Error getting progress: {e}")
        return None


def _get_progress_impl():
    """Internal implementation of get_progress (assumes context exists)."""
    try:
        progress = Progress.query.first()
        if progress:
            return {
                'total': progress.total,
                'current': progress.current,
                'status': progress.status,
                'details': progress.details,
                'stats': progress.stats or {}
            }
        return None
    except Exception as e:
        print(f"⚠️ Error getting progress: {e}")
        return None


def get_latest_report():
    """
    Gets the latest processing report from database.
    
    Returns:
        Report object or None
    """
    try:
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _get_latest_report_impl()
        else:
            return _get_latest_report_impl()
    except Exception as e:
        print(f"⚠️ Error getting latest report: {e}")
        return None


def _get_latest_report_impl():
    """Internal implementation of get_latest_report (assumes context exists)."""
    try:
        return Report.query.order_by(Report.timestamp.desc()).first()
    except Exception as e:
        print(f"⚠️ Error getting latest report: {e}")
        return None


def get_followup_stats():
    """
    Gets follow-up statistics from database.
    
    Returns:
        Dictionary with follow-up stats
    """
    try:
        if not has_app_context():
            app = create_app()
            with app.app_context():
                return _get_followup_stats_impl()
        else:
            return _get_followup_stats_impl()
    except Exception as e:
        print(f"⚠️ Error getting followup stats: {e}")
        return {}


def _get_followup_stats_impl():
    """Internal implementation of get_followup_stats (assumes context exists)."""
    try:
        from datetime import date
        
        total_pending = ActionLog.query.filter_by(is_followup_pending=True, followup_sent=False).count()
        total_sent = ActionLog.query.filter_by(followup_sent=True).count()
        today = date.today()
        
        overdue = ActionLog.query.filter(
            ActionLog.is_followup_pending == True,
            ActionLog.followup_sent == False,
            ActionLog.expected_reply_date < today
        ).count()
        
        return {
            'pending': total_pending,
            'sent': total_sent,
            'overdue': overdue
        }
    except Exception as e:
        print(f"⚠️ Error getting followup stats: {e}")
        return {}
