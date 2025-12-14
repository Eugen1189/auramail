@echo off
echo Checking git status...
git status

echo.
echo Adding all changes...
git add -A

echo.
echo Committing changes...
git commit -m "Fix: Session management, database initialization, worker context, and Gmail label colors

- Fixed Flask session configuration for OAuth callback (SESSION_COOKIE_SECURE in DEBUG mode)
- Added automatic database table creation in app_factory.py
- Fixed Flask app context for ThreadPoolExecutor threads in tasks.py
- Updated Gmail label colors to use color names instead of HEX codes
- Added fallback logic for label color creation (create without color if color fails)
- Updated init_database.py to use app_factory.create_app() for consistency
- Fixed worker.py to properly wrap tasks with Flask app context
- Updated LABEL_COLOR_MAP to use Gmail API color names (blue, red, orange, etc.)
- Removed FLASK_SECRET_KEY default value for security
- Added session.permanent = True in before_request middleware"

echo.
echo Final status:
git status

pause

