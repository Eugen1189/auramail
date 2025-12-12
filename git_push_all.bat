@echo off
chcp 65001 >nul
echo ========================================
echo  Збереження всіх змін до GitHub
echo ========================================
echo.

echo [1/6] Перевірка статусу Git...
git status
echo.

echo [2/6] Додавання всіх файлів...
git add -A
echo.

echo [3/6] Перевірка доданих файлів...
git status --short
echo.

echo [4/6] Створення коміту...
git commit -m "feat: Complete AuraMail project with 66%% test coverage and CI/CD

- Added 60 tests covering all critical modules (66%% coverage)
- Implemented async processing with RQ worker
- Migrated to PostgreSQL/SQLite database with Alembic migrations
- Added security features: Flask-Talisman, CORS, Secret Management
- Implemented rate limiting and retry logic for Gemini API
- Unified web interface with real-time progress tracking
- Complete CI/CD pipeline with GitHub Actions
- Comprehensive documentation

Test Coverage:
- utils/db_logger.py: 75%%
- utils/gemini_processor.py: 74%%
- utils/gmail_api.py: 66%%
- database.py: 95%%"
echo.

echo [5/6] Перевірка remote репозиторію...
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo Додавання remote origin...
    git remote add origin https://github.com/Eugen1189/auramail.git
) else (
    echo Оновлення remote origin...
    git remote set-url origin https://github.com/Eugen1189/auramail.git
)
git remote -v
echo.

echo [6/6] Встановлення гілки main...
git branch -M main
echo.

echo [7/7] Відправка до GitHub...
echo.
echo ВАЖЛИВО: Якщо запитує автентифікацію:
echo - Username: ваш GitHub username
echo - Password: використайте Personal Access Token (не пароль!)
echo    Створіть токен тут: https://github.com/settings/tokens
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
    echo.
) else (
    echo.
    echo ========================================
    echo  Успішно відправлено!
    echo ========================================
    echo Репозиторій: https://github.com/Eugen1189/auramail
    echo.
)

pause

