# PowerShell script to push all changes to GitHub
# Run: .\git_push_all.ps1

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Збереження всіх змін до GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/7] Перевірка статусу Git..." -ForegroundColor Yellow
git status
Write-Host ""

Write-Host "[2/7] Додавання всіх файлів..." -ForegroundColor Yellow
git add -A
Write-Host ""

Write-Host "[3/7] Перевірка доданих файлів..." -ForegroundColor Yellow
$files = git status --short
if ($files) {
    Write-Host "Додані/змінені файли:" -ForegroundColor Green
    git status --short
} else {
    Write-Host "Немає нових змін для коміту" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[4/7] Створення коміту..." -ForegroundColor Yellow
$commitMessage = @"
feat: Complete AuraMail project with 66% test coverage and CI/CD

- Added 60 tests covering all critical modules (66% coverage)
- Implemented async processing with RQ worker
- Migrated to PostgreSQL/SQLite database with Alembic migrations
- Added security features: Flask-Talisman, CORS, Secret Management
- Implemented rate limiting and retry logic for Gemini API
- Unified web interface with real-time progress tracking
- Complete CI/CD pipeline with GitHub Actions
- Comprehensive documentation

Test Coverage:
- utils/db_logger.py: 75%
- utils/gemini_processor.py: 74%
- utils/gmail_api.py: 66%
- database.py: 95%
"@

git commit -m $commitMessage
Write-Host ""

Write-Host "[5/7] Перевірка remote репозиторію..." -ForegroundColor Yellow
try {
    $remote = git remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Додавання remote origin..." -ForegroundColor Yellow
        git remote add origin https://github.com/Eugen1189/auramail.git
    } else {
        Write-Host "Оновлення remote origin..." -ForegroundColor Yellow
        git remote set-url origin https://github.com/Eugen1189/auramail.git
    }
    git remote -v
} catch {
    Write-Host "Помилка при налаштуванні remote: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "[6/7] Встановлення гілки main..." -ForegroundColor Yellow
git branch -M main
Write-Host ""

Write-Host "[7/7] Відправка до GitHub..." -ForegroundColor Yellow
Write-Host ""
Write-Host "ВАЖЛИВО: Якщо запитує автентифікацію:" -ForegroundColor Yellow
Write-Host "- Username: ваш GitHub username" -ForegroundColor White
Write-Host "- Password: використайте Personal Access Token (не пароль!)" -ForegroundColor White
Write-Host "  Створіть токен тут: https://github.com/settings/tokens" -ForegroundColor White
Write-Host ""

git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " Успішно відправлено!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Репозиторій: https://github.com/Eugen1189/auramail" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " Помилка при відправці!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Перевірте:" -ForegroundColor Yellow
    Write-Host "1. Є підключення до інтернету" -ForegroundColor White
    Write-Host "2. Ви маєте доступ до репозиторію" -ForegroundColor White
    Write-Host "3. Ви використали правильний Personal Access Token" -ForegroundColor White
}

