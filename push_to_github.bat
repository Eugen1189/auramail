@echo off
REM Batch script to push code to GitHub
REM Run: push_to_github.bat

echo 🔍 Checking git status...
git status

echo.
echo 📦 Adding all files...
git add .

echo.
echo 📝 Creating commit...
git commit -m "feat: Add comprehensive test coverage (66%%) and CI/CD pipeline - Added 39 new tests covering critical modules - Total: 60 tests, 66%% code coverage - Implemented complete CI/CD pipeline - Production readiness improvements"

echo.
echo 🔗 Checking remote repository...
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo Adding remote origin...
    git remote add origin https://github.com/Eugen1189/auramail.git
) else (
    git remote set-url origin https://github.com/Eugen1189/auramail.git
)

echo.
echo 🌿 Setting branch to main...
git branch -M main

echo.
echo 🚀 Pushing to GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo ❌ Push failed. Please check the error above.
) else (
    echo.
    echo ✅ Successfully pushed to GitHub!
    echo Repository: https://github.com/Eugen1189/auramail
)

pause








