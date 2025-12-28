@echo off
echo ========================================
echo Checking Git Status and Remote
echo ========================================
echo.

echo [1/5] Checking git status...
git status
echo.

echo [2/5] Checking remote repository...
git remote -v
echo.

echo [3/5] Adding all changes...
git add -A
echo.

echo [4/5] Committing changes...
git commit -m "Fix: Session management, database initialization, worker context, and Gmail label colors - Fixed Flask session configuration for OAuth callback - Added automatic database table creation - Fixed Flask app context for ThreadPoolExecutor threads - Updated Gmail label colors to use color names - Added fallback logic for label color creation"
echo.

echo [5/5] Pushing to remote...
git push
echo.

echo ========================================
echo Final status:
echo ========================================
git status
echo.

echo Done!
pause










