import json
import os
import datetime
from datetime import timedelta
from config import LOG_FILE, PROGRESS_FILE

# --- LOGGING FUNCTIONS (HISTORY) ---

def log_action(msg_id, classification, action_taken, subject):
    """Logs action to JSON file."""
    entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'msg_id': msg_id,
        'message_id': msg_id,              # alias for templates expecting message_id
        'subject': subject,
        'original_subject': subject,       # alias for templates expecting original_subject
        'ai_category': classification.get('category', 'UNKNOWN'),
        'action_taken': action_taken,
        'reason': classification.get('description', ''),
        'ai_description': classification.get('description', ''),  # alias for template
        'details': classification
    }
    
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
            
        logs.append(entry)
        
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error logging action: {e}")

def get_log_entry(msg_id):
    """Finds a specific log entry by message ID."""
    try:
        if not os.path.exists(LOG_FILE):
            return None
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = json.load(f)
            for entry in logs:
                if entry['msg_id'] == msg_id:
                    return entry
        return None
    except Exception:
        return None

def get_action_history(limit=50):
    """Returns recent actions."""
    try:
        if not os.path.exists(LOG_FILE):
            return []
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        return logs[-limit:]
    except Exception:
        return []

def get_daily_stats(days=7):
    """Calculates stats for the last N days."""
    stats = {}
    try:
        if not os.path.exists(LOG_FILE):
            return stats
            
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = json.load(f)
            
        now = datetime.datetime.now()
        for i in range(days):
            date_str = (now - timedelta(days=i)).strftime('%Y-%m-%d')
            stats[date_str] = 0
            
        for entry in logs:
            ts = entry.get('timestamp', '')[:10]  # YYYY-MM-DD
            if ts in stats:
                stats[ts] += 1
                
        return stats
    except Exception:
        return stats

# --- PROGRESS TRACKING FUNCTIONS (FIXED) ---

def init_progress(total=0):
    """
    Initializes the progress file with total items count.
    Accepts 'total' argument to fix the error.
    """
    data = {
        'total': total,
        'current': 0,
        'status': 'Starting...',
        'details': 'Initializing...',
        'stats': {}
    }
    _save_progress(data)

def update_progress(current, stats=None, details=''):
    """Updates current progress."""
    data = _load_progress()
    # Support both old and new field names for compatibility
    data['current'] = current
    data['current_message'] = current  # For frontend compatibility
    data['total_messages'] = data.get('total', 0)  # For frontend compatibility
    if stats:
        data['stats'] = stats
        data['statistics'] = stats  # For frontend compatibility
    if details:
        data['details'] = details
        data['current_email_subject'] = details  # For frontend compatibility
    # Calculate progress percentage
    total = data.get('total', 0)
    if total > 0:
        data['progress_percentage'] = int((current / total) * 100)
    else:
        data['progress_percentage'] = 0
    data['status'] = 'Processing...'
    _save_progress(data)

def complete_progress(stats=None):
    """Marks process as complete."""
    data = _load_progress()
    total = data.get('total', 0)
    data['current'] = total
    data['current_message'] = total  # For frontend compatibility
    data['total_messages'] = total  # For frontend compatibility
    data['status'] = 'Completed'
    data['details'] = 'Done'
    data['progress_percentage'] = 100
    if stats:
        data['stats'] = stats
        data['statistics'] = stats  # For frontend compatibility
    _save_progress(data)

def get_progress():
    """Reads current progress."""
    return _load_progress()

def _save_progress(data):
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving progress: {e}")

def _load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return {'total': 0, 'current': 0, 'status': 'Idle', 'details': ''}
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'total': 0, 'current': 0, 'status': 'Error', 'details': ''}
