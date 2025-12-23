"""
Database logging module for AuraMail.
Replaces JSON file-based logging with database-backed logging.
Uses SQLAlchemy models: ActionLog, Report, Progress.
"""
import os
from datetime import datetime, date
from flask import current_app
from database import db, ActionLog, Report, Progress


def log_action(msg_id, classification, action_taken, subject):
    """
    Logs action to database (ActionLog table).
    
    Args:
        msg_id: Email message ID
        classification: Dictionary with category, description, expected_reply_date, etc.
        action_taken: Action performed (MOVE, ARCHIVE, DELETE, etc.)
        subject: Email subject
    
    Returns:
        None (logs to database)
    """
    try:
        # Parse expected_reply_date if present
        expected_reply_date = None
        expects_reply = classification.get('expects_reply', False)
        
        # CRITICAL FIX: Only parse expected_reply_date if it's not None/empty
        # This ensures that when Gemini returns None, we don't set a date
        if 'expected_reply_date' in classification and classification['expected_reply_date']:
            expected_reply_date_str = classification['expected_reply_date']
            # CRITICAL: Check if it's actually None or empty string
            if expected_reply_date_str is None or expected_reply_date_str == '':
                expected_reply_date = None
            else:
                try:
                    # Try ISO format first (2025-12-31T10:00:00)
                    if 'T' in str(expected_reply_date_str):
                        expected_reply_date = datetime.fromisoformat(str(expected_reply_date_str).replace('Z', '+00:00')).date()
                    else:
                        # Try strptime format (2025-12-31)
                        expected_reply_date = datetime.strptime(str(expected_reply_date_str), '%Y-%m-%d').date()
                except (ValueError, AttributeError, TypeError):
                    # Invalid date format, leave as None
                    expected_reply_date = None
        
        # Check if entry already exists (update instead of create)
        # Ensure session is active before querying - with reconnect logic for fault tolerance
        existing_entry = None
        max_reconnect_attempts = 3
        
        # First, ensure session is clean before querying
        # CRITICAL: Always rollback first to clear any pending transactions
        # This prevents PendingRollbackError from propagating between tests
        try:
            # Check if session has pending rollback
            if db.session.is_active:
                try:
                    db.session.rollback()
                except Exception:
                    # If rollback fails, try to remove session
                    try:
                        db.session.remove()
                    except Exception:
                        pass
        except Exception:
            # If checking session state fails, try to rollback anyway
            try:
                db.session.rollback()
            except Exception:
                pass
        
        for attempt in range(max_reconnect_attempts):
            try:
                # CRITICAL FIX: Переконуємося, що сесія активна перед запитом
                # Це запобігає "Database session closed" помилкам
                try:
                    # Перевіряємо, чи сесія активна
                    if not db.session.is_active:
                        # Сесія неактивна - намагаємося її активувати
                        try:
                            db.session.rollback()
                        except Exception:
                            pass
                        try:
                            db.session.remove()
                        except Exception:
                            pass
                except Exception:
                    # Якщо перевірка не вдалася, пробуємо rollback
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                
                # Check if session is active
                try:
                    # Try to query for existing entry
                    existing_entry = ActionLog.query.filter_by(msg_id=msg_id).first()
                    break  # Success, exit retry loop
                except Exception as query_error:
                    error_str = str(query_error).lower()
                    is_closed_error = 'closed' in error_str or 'invalid transaction' in error_str or 'pendingrollback' in error_str
                    
                    if is_closed_error and attempt < max_reconnect_attempts - 1:
                        # Session is closed or has pending rollback - try to reconnect (Fault Tolerance)
                        try:
                            # First, try to rollback to clear any pending rollback
                            try:
                                db.session.rollback()
                            except Exception:
                                pass
                            
                            # Remove session to force new connection
                            try:
                                db.session.remove()
                            except Exception:
                                pass
                            
                            # Try to refresh session by executing a simple query
                            # This forces SQLAlchemy to create a new connection
                            try:
                                # Use a simple query to test connection
                                db.session.execute(db.text('SELECT 1'))
                                db.session.commit()
                                # If successful, retry the original query
                                continue
                            except Exception:
                                # If reconnect fails, wait a bit before retrying
                                import time
                                time.sleep(0.01 * (attempt + 1))  # Small delay with backoff
                                continue
                        except Exception:
                            # If all reconnect attempts fail, wait and retry
                            import time
                            time.sleep(0.01 * (attempt + 1))
                            continue
                    else:
                        # If not a closed error or max attempts reached, re-raise
                        if os.environ.get('TESTING') or os.environ.get('PYTEST_CURRENT_TEST'):
                            if is_closed_error:
                                raise Exception(f"Database session closed during query (test isolation issue): {query_error}") from query_error
                        raise
            except Exception as e:
                if attempt == max_reconnect_attempts - 1:
                    # Last attempt failed - re-raise
                    raise
                # Wait a bit before retry
                import time
                time.sleep(0.01 * (attempt + 1))
        
        # Ensure ai_category is never None (nullable=False constraint)
        # Use 'or' operator to handle both missing key and None value cases
        ai_category = classification.get('category') or 'UNKNOWN'
        reason = classification.get('description') or ''
        
        if existing_entry:
            # Update existing entry
            existing_entry.subject = subject
            existing_entry.ai_category = ai_category
            existing_entry.action_taken = action_taken
            existing_entry.reason = reason
            existing_entry.details = classification
            existing_entry.expected_reply_date = expected_reply_date
            existing_entry.is_followup_pending = expects_reply
            existing_entry.timestamp = datetime.utcnow()
            # Flush immediately to reduce transaction time
            db.session.flush()
        else:
            # Create new entry
            new_entry = ActionLog(
                msg_id=msg_id,
                subject=subject,
                ai_category=ai_category,
                action_taken=action_taken,
                reason=reason,
                details=classification,
                expected_reply_date=expected_reply_date,
                is_followup_pending=expects_reply,
                followup_sent=False
            )
            db.session.add(new_entry)
            # Flush immediately to reduce transaction time
            db.session.flush()
        
        # Retry mechanism for database locking issues (especially for SQLite)
        # Increased retries for better reliability in test environment
        max_retries = 10  # Increased from 5 to 10 for better reliability
        retry_delay = 0.05  # 50ms initial delay
        
        for attempt in range(max_retries):
            try:
                # Flush before commit to catch errors early
                db.session.flush()
                db.session.commit()
                break  # Success, exit retry loop
            except Exception as db_error:
                # Always rollback on error to clear transaction state
                try:
                    db.session.rollback()
                except Exception:
                    pass
                
                # Check if it's a locking error (SQLite specific)
                error_str = str(db_error).lower()
                is_locking_error = 'locked' in error_str or 'database is locked' in error_str
                
                if is_locking_error and attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    import time
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential: 50ms, 100ms, 200ms, 400ms, 800ms
                    # Clear session state and re-add object
                    try:
                        db.session.expunge_all()  # Clear session state
                        # Re-add the entry if it was removed
                        if existing_entry:
                            db.session.add(existing_entry)
                        else:
                            db.session.add(new_entry)
                    except Exception:
                        pass
                    continue
                else:
                    # If not a locking error or max retries reached, break and handle in outer except
                    # Don't raise here - let outer except handle it gracefully
                    break
        
        # Expire all objects to ensure fresh state (helps with in-memory SQLite)
        # This ensures queries see the latest data
        db.session.expire_all()
        
        # Note: We don't close the session here because it's managed by Flask-SQLAlchemy
        # The session will be automatically cleaned up by the app context
        # Closing it manually could cause issues with subsequent operations
    except Exception as e:
        # Rollback on error - ALWAYS rollback before handling error
        # This ensures session is in a clean state
        try:
            db.session.rollback()
        except Exception:
            # If rollback fails, try to close and remove session
            try:
                db.session.close()
            except Exception:
                pass
            try:
                db.session.remove()
            except Exception:
                pass
        
        # Expire all objects to clear session state
        try:
            db.session.expire_all()
        except Exception:
            pass
        
        # In test environment, raise exception to fail fast and identify issues
        # In production, log error gracefully
        if os.environ.get('TESTING') or os.environ.get('PYTEST_CURRENT_TEST'):
            # Check if it's a closed database error - this indicates test isolation issue
            error_str = str(e).lower()
            if 'closed' in error_str or 'invalid transaction' in error_str:
                # Database was closed - this is a test isolation issue
                raise Exception(f"Database session closed (test isolation issue): {e}") from e
            # Re-raise in test environment to catch issues early
            raise Exception(f"Error logging action (test mode): {e}") from e
        else:
            # In production, log gracefully
            print(f"Error logging action: {e}")
            # Function should handle errors gracefully and not raise exceptions in production


def get_log_entry(msg_id):
    """
    Retrieves a specific log entry by message ID.
    
    Args:
        msg_id: Email message ID
    
    Returns:
        Dictionary representation of ActionLog entry, or None if not found
    """
    try:
        entry = ActionLog.query.filter_by(msg_id=msg_id).first()
        if entry:
            return entry.to_dict()
        return None
    except Exception:
        return None


def get_action_history(limit=50):
    """
    Returns recent action history.
    
    Args:
        limit: Maximum number of entries to return (default: 50)
    
    Returns:
        List of dictionaries representing ActionLog entries
    """
    try:
        entries = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(limit).all()
        return [entry.to_dict() for entry in entries]
    except Exception:
        return []


def get_daily_stats(days=7):
    """
    Calculates statistics for the last N days.
    
    Args:
        days: Number of days to calculate stats for (default: 7)
    
    Returns:
        Dictionary with date strings as keys and counts as values
    """
    try:
        from datetime import timedelta
        
        stats = {}
        now = datetime.utcnow()
        
        # Initialize stats for last N days
        for i in range(days):
            date_str = (now - timedelta(days=i)).date().isoformat()
            stats[date_str] = 0
        
        # Query entries from last N days
        start_date = (now - timedelta(days=days)).date()
        entries = ActionLog.query.filter(
            ActionLog.timestamp >= datetime.combine(start_date, datetime.min.time())
        ).all()
        
        # Count entries per day
        for entry in entries:
            entry_date = entry.timestamp.date().isoformat()
            if entry_date in stats:
                stats[entry_date] += 1
        
        return stats
    except Exception:
        return {}


def save_report(stats):
    """
    Saves a processing report to database.
    
    Args:
        stats: Dictionary with report statistics:
            - total_processed
            - important
            - action_required
            - newsletter
            - social
            - review
            - archived
            - errors
    
    Returns:
        None (saves to database)
    """
    try:
        new_report = Report(
            total_processed=stats.get('total_processed', 0),
            important=stats.get('important', 0),
            action_required=stats.get('action_required', 0),
            newsletter=stats.get('newsletter', 0),
            social=stats.get('social', 0),
            review=stats.get('review', 0),
            archived=stats.get('archived', 0),
            errors=stats.get('errors', 0),
            stats=stats
        )
        db.session.add(new_report)
        
        # Retry mechanism for database locking issues
        # Increased retries for better reliability in test environment
        max_retries = 10  # Increased from 5 to 10 for better reliability
        retry_delay = 0.05  # 50ms initial delay
        
        for attempt in range(max_retries):
            try:
                db.session.flush()
                db.session.commit()
                break  # Success, exit retry loop
            except Exception as db_error:
                # Check if it's a locking error
                error_str = str(db_error).lower()
                is_locking_error = 'locked' in error_str or 'database is locked' in error_str
                
                if is_locking_error and attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    import time
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    # Rollback and clear session state
                    try:
                        db.session.rollback()
                        db.session.expunge_all()
                    except Exception:
                        pass
                    continue
                else:
                    # If not a locking error or max retries reached, break and handle in outer except
                    break
        
        # Invalidate cache if available (non-critical, errors are silently ignored)
        try:
            _invalidate_cache()
        except Exception:
            # Cache invalidation errors are non-critical and should not fail the operation
            pass
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        
        # In test environment, raise exception to fail fast and identify issues
        # In production, log error gracefully
        # Exception: Cache errors are always ignored (non-critical)
        is_cache_error = 'cache' in str(e).lower() or 'ImportError' in str(type(e).__name__)
        if (os.environ.get('TESTING') or os.environ.get('PYTEST_CURRENT_TEST')) and not is_cache_error:
            # Re-raise in test environment to catch issues early (except cache errors)
            raise Exception(f"Error saving report (test mode): {e}") from e
        else:
            # In production, log gracefully
            print(f"Error saving report: {e}")


def get_latest_report():
    """
    Retrieves the most recent report.
    
    Returns:
        Dictionary representation of latest Report entry, or default empty report if no reports exist
    """
    try:
        report = Report.query.order_by(Report.created_at.desc()).first()
        if report:
            return report.to_dict()
        # ПОВЕРТАЄМО ДЕФОЛТНИЙ СЛОВНИК ЗАМІСТЬ NONE
        # Формат відповідає Report.to_dict() для сумісності
        return {
            'total_processed': 0,
            'important': 0,
            'action_required': 0,
            'newsletter': 0,
            'social': 0,
            'review': 0,
            'archived': 0,
            'errors': 0
        }
    except Exception as e:
        print(f"Error getting latest report: {e}")
        # Повертаємо дефолтний словник з помилкою
        return {
            'total_processed': 0,
            'important': 0,
            'action_required': 0,
            'newsletter': 0,
            'social': 0,
            'review': 0,
            'archived': 0,
            'errors': 0
        }


def init_progress(total=0):
    """
    Initializes progress tracking in database.
    Deletes old progress entries and creates a new one.
    
    Args:
        total: Total number of items to process (default: 0)
    
    Returns:
        None (saves to database)
    """
    try:
        # Delete all existing progress entries (only one should exist)
        Progress.query.delete()
        
        new_progress = Progress(
            total=total,
            current=0,
            status='Starting...',
            details='Initializing...',
            stats={}
        )
        db.session.add(new_progress)
        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f"Error initializing progress: {e}")


def update_progress(current, stats=None, details=''):
    """
    Updates current progress in database.
    
    Args:
        current: Current number of processed items
        stats: Optional statistics dictionary
        details: Optional status details string
    
    Returns:
        None (updates database)
    """
    try:
        # Get existing progress or create new one
        progress = Progress.query.first()
        if not progress:
            progress = Progress(total=0, current=0, status='Running', details='', stats={})
            db.session.add(progress)
        
        progress.current = current
        progress.status = 'Running'
        if details:
            progress.details = details
        if stats:
            progress.stats = stats
        
        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f"Error updating progress: {e}")


def complete_progress(stats=None, details=None):
    """
    Marks progress as completed in database.
    
    CRITICAL FIX: Sets current = total to show 100% completion in UI.
    This fixes the issue where Early Exit shows 0/17 instead of 17/17.
    
    Args:
        stats: Optional statistics dictionary to save with progress
        details: Optional completion message (default: 'Processing complete' or 'Ваша пошта вже в ідеальному порядку')
    
    Returns:
        None (updates database)
    """
    try:
        progress = Progress.query.first()
        if progress:
            # CRITICAL: Set current = total to show 100% completion
            # This ensures UI shows correct progress even for Early Exit scenarios
            progress.current = progress.total
            progress.status = 'Completed'
            
            # Use custom message if provided, otherwise use default
            if details:
                progress.details = details
            elif progress.total == 0:
                progress.details = 'Ваша пошта вже в ідеальному порядку. AI відпочиває.'
            else:
                progress.details = 'Ваша пошта успішно розсортована!'
            
            # Save stats if provided
            if stats:
                progress.stats = stats
            db.session.commit()
        else:
            # If no progress exists, create one with completed status
            # For Early Exit: total might be 0, but we still show completion
            total = stats.get('total_processed', 0) if stats else 0
            progress = Progress(
                total=total,
                current=total,  # CRITICAL: Set current = total for 100%
                status='Completed',
                details=details or 'Ваша пошта вже в ідеальному порядку. AI відпочиває.',
                stats=stats or {}
            )
            db.session.add(progress)
            db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f"Error completing progress: {e}")


def get_progress():
    """
    Retrieves current progress from database.
    
    Returns:
        Dictionary representation of Progress entry, or default empty progress if no progress exists
    """
    try:
        progress = Progress.query.first()
        if progress:
            return progress.to_dict()
        # ПОВЕРТАЄМО ДЕФОЛТНИЙ СЛОВНИК ЗАМІСТЬ NONE
        # Формат відповідає Progress.to_dict() для сумісності
        return {
            "total": 0,
            "current": 0,
            "current_message": 0,
            "total_messages": 0,
            "status": "idle",
            "details": "",
            "current_email_subject": "",
            "stats": {},
            "statistics": {},
            "progress_percentage": 0
        }
    except Exception as e:
        print(f"Error getting progress: {e}")
        # Повертаємо дефолтний словник з помилкою
        return {
            "total": 0,
            "current": 0,
            "current_message": 0,
            "total_messages": 0,
            "status": "error",
            "details": str(e),
            "current_email_subject": str(e),
            "stats": {},
            "statistics": {},
            "progress_percentage": 0
        }


def get_followup_stats():
    """
    Retrieves follow-up statistics from database.
    
    Returns:
        Dictionary with 'pending' and 'overdue' counts
    """
    try:
        from datetime import date
        
        # Count pending follow-ups
        pending = ActionLog.query.filter(
            ActionLog.is_followup_pending == True,
            ActionLog.followup_sent == False
        ).count()
        
        # Count overdue follow-ups (expected_reply_date < today)
        today = date.today()
        overdue = ActionLog.query.filter(
            ActionLog.is_followup_pending == True,
            ActionLog.followup_sent == False,
            ActionLog.expected_reply_date < today
        ).count()
        
        return {
            'pending': pending,
            'overdue': overdue
        }
    except Exception:
        # Return default values on error
        return {'pending': 0, 'overdue': 0}


def _invalidate_cache():
    """
    Invalidates cache for dashboard statistics.
    This is a helper function that tries to invalidate cache if cache_helper is available.
    """
    try:
        from utils.cache_helper import invalidate_dashboard_cache
        invalidate_dashboard_cache()
    except ImportError:
        # Cache helper not available, silently ignore
        pass
    except Exception:
        # Other errors, silently ignore
        pass
