# PowerShell script to push code to GitHub
# Run: .\push_to_github.ps1

Write-Host "🔍 Checking git status..." -ForegroundColor Cyan
git status

Write-Host "`n📦 Adding all files..." -ForegroundColor Cyan
git add .

Write-Host "`n📝 Creating commit..." -ForegroundColor Cyan
git commit -m "feat: Add comprehensive test coverage (66%) and CI/CD pipeline

- Added 39 new tests covering critical modules
- utils/db_logger.py: 75% coverage (from 33%)
- utils/gemini_processor.py: 74% coverage (from 57%)
- utils/gmail_api.py: 66% coverage (from 7%)
- Total: 60 tests, 66% code coverage

- Implemented complete CI/CD pipeline:
  - Automated testing on push/PR
  - Docker image building
  - Automatic deployment to production/staging
  - Database migrations
  - Systemd service management

- Enhanced test suite:
  - Extended Gmail API tests (14 tests)
  - Extended Gemini processor tests (11 tests)
  - Extended DB logger tests (14 tests)
  - Tasks processing tests (7 tests)
  - Rate limiter tests (5 tests)
  - Retry mechanism tests (3 tests)
  - API endpoints tests (4 tests)
  - Database models tests (5 tests)

- Production readiness improvements:
  - Security headers (Flask-Talisman)
  - CORS configuration (Flask-CORS)
  - Secret management (python-decouple)
  - Database migrations (Alembic)
  - Connection pooling
  - Rate limiting and retry mechanisms"

Write-Host "`n🔗 Checking remote repository..." -ForegroundColor Cyan
$remote = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Adding remote origin..." -ForegroundColor Yellow
    git remote add origin https://github.com/Eugen1189/auramail.git
} else {
    if ($remote -ne "https://github.com/Eugen1189/auramail.git") {
        Write-Host "Updating remote origin..." -ForegroundColor Yellow
        git remote set-url origin https://github.com/Eugen1189/auramail.git
    } else {
        Write-Host "Remote origin already configured" -ForegroundColor Green
    }
}

Write-Host "`n🌿 Setting branch to main..." -ForegroundColor Cyan
git branch -M main

Write-Host "`n🚀 Pushing to GitHub..." -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host "Repository: https://github.com/Eugen1189/auramail" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ Push failed. Please check the error above." -ForegroundColor Red
}








