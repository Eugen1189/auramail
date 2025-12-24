"""
Script to clear ActionLog database table.
Removes all old entries, especially those with 'DANGER' category that might interfere with statistics.

Usage:
    python clear_database.py

WARNING: This will delete ALL entries from action_logs table!
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_factory import create_app
from database import db, ActionLog, Progress, Report

def clear_action_logs():
    """Clear all entries from ActionLog table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Count entries before deletion
            count_before = ActionLog.query.count()
            danger_count = ActionLog.query.filter(ActionLog.ai_category == 'DANGER').count()
            
            print(f"📊 Current database state:")
            print(f"   Total entries: {count_before}")
            print(f"   DANGER entries: {danger_count}")
            
            if count_before == 0:
                print("✅ Database is already empty. Nothing to clear.")
                return
            
            # Ask for confirmation
            print(f"\n⚠️  WARNING: This will delete ALL {count_before} entries from action_logs table!")
            response = input("Type 'yes' to confirm: ")
            
            if response.lower() != 'yes':
                print("❌ Operation cancelled.")
                return
            
            # Delete all entries
            ActionLog.query.delete()
            db.session.commit()
            
            print(f"✅ Successfully deleted {count_before} entries from action_logs table.")
            print(f"   (Including {danger_count} DANGER entries)")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing database: {e}")
            import traceback
            traceback.print_exc()
            return


def clear_all_tables():
    """Clear all tables (ActionLog, Progress, Report)."""
    app = create_app()
    
    with app.app_context():
        try:
            action_logs_count = ActionLog.query.count()
            progress_count = Progress.query.count()
            report_count = Report.query.count()
            
            print(f"📊 Current database state:")
            print(f"   ActionLog entries: {action_logs_count}")
            print(f"   Progress entries: {progress_count}")
            print(f"   Report entries: {report_count}")
            
            total = action_logs_count + progress_count + report_count
            if total == 0:
                print("✅ Database is already empty. Nothing to clear.")
                return
            
            # Ask for confirmation
            print(f"\n⚠️  WARNING: This will delete ALL entries from ALL tables!")
            response = input("Type 'yes' to confirm: ")
            
            if response.lower() != 'yes':
                print("❌ Operation cancelled.")
                return
            
            # Delete all entries
            ActionLog.query.delete()
            Progress.query.delete()
            Report.query.delete()
            db.session.commit()
            
            print(f"✅ Successfully cleared all tables:")
            print(f"   - Deleted {action_logs_count} ActionLog entries")
            print(f"   - Deleted {progress_count} Progress entries")
            print(f"   - Deleted {report_count} Report entries")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing database: {e}")
            import traceback
            traceback.print_exc()
            return


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear AuraMail database tables')
    parser.add_argument('--all', action='store_true', help='Clear all tables (ActionLog, Progress, Report)')
    parser.add_argument('--action-logs-only', action='store_true', help='Clear only ActionLog table (default)')
    
    args = parser.parse_args()
    
    if args.all:
        clear_all_tables()
    else:
        clear_action_logs()

