#!/usr/bin/env python3
"""
Script to commit changes to git repository.
"""
import subprocess
import sys

def run_git_command(cmd):
    """Run git command and return output."""
    try:
        result = subprocess.run(
            ['git'] + cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=False
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("🔄 Checking git status...")
    success, stdout, stderr = run_git_command(['status'])
    if not success:
        print(f"❌ Error checking git status: {stderr}")
        return 1
    
    print(stdout)
    
    print("\n📦 Adding all changes...")
    success, stdout, stderr = run_git_command(['add', '-A'])
    if not success:
        print(f"❌ Error adding files: {stderr}")
        return 1
    
    print("✅ Files added")
    
    print("\n📝 Committing changes...")
    commit_message = """Fix: Session management, database initialization, worker context, and Gmail label colors

- Fixed Flask session configuration for OAuth callback (SESSION_COOKIE_SECURE in DEBUG mode)
- Added automatic database table creation in app_factory.py
- Fixed Flask app context for ThreadPoolExecutor threads in tasks.py
- Updated Gmail label colors to use color names instead of HEX codes
- Added fallback logic for label color creation (create without color if color fails)
- Updated init_database.py to use app_factory.create_app() for consistency
- Fixed worker.py to properly wrap tasks with Flask app context
- Updated LABEL_COLOR_MAP to use Gmail API color names (blue, red, orange, etc.)
- Removed FLASK_SECRET_KEY default value for security
- Added session.permanent = True in before_request middleware"""
    
    success, stdout, stderr = run_git_command(['commit', '-m', commit_message])
    if not success:
        print(f"❌ Error committing: {stderr}")
        return 1
    
    print("✅ Changes committed successfully!")
    print(stdout)
    
    print("\n📊 Final status:")
    success, stdout, stderr = run_git_command(['status'])
    if success:
        print(stdout)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

