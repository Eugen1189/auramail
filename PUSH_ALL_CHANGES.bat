@echo off
chcp 65001 >nul
echo ========================================
echo  Push всіх змін до GitHub
echo ========================================
echo.

echo [1/6] Перевірка статусу Git...
git status
echo.

echo [2/6] Додавання всіх файлів...
git add -A
echo.

echo [3/6] Створення коміту з останніми виправленнями...
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

echo [4/6] Перевірка remote репозиторію...
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo Додавання remote origin...
    git remote add origin https://github.com/Eugen1189/auramail.git
) else (
    echo Remote origin вже налаштований
)
git remote -v
echo.

echo [5/6] Встановлення гілки main...
git branch -M main
echo.

echo [6/6] Відправка до GitHub...
echo.
echo ВАЖЛИВО: Якщо запитує автентифікацію:
echo - Username: ваш GitHub username (Eugen1189)
echo - Password: використайте Personal Access Token (не пароль!)
echo    Створіть токен тут: https://github.com/settings/tokens
echo    Потрібні права: repo (повний доступ до репозиторіїв)
echo.
git push -u origin main

if errorlevel 1 (
    echo.
    echo ========================================
    echo  Помилка при відправці!
    echo ========================================
    echo Перевірте:
    echo 1. Є підключення до інтернету
    echo 2. Ви маєте доступ до репозиторію
    echo 3. Ви використали правильний Personal Access Token
    echo 4. Репозиторій існує на GitHub
    echo.
) else (
    echo.
    echo ========================================
    echo  ✅ Успішно відправлено!
    echo ========================================
    echo Репозиторій: https://github.com/Eugen1189/auramail
    echo.
)

pause







