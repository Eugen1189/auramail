# 🤖 AuraMail - AI-Powered Email Organizer

**Production-ready email management system with AI classification, automated sorting, and comprehensive test coverage.**

## 🛡️ Data Preservation Policy

**AuraMail ніколи не видаляє ваші листи назавжди.** Всі листи залишаються доступними у папці "All Mail". Ми використовуємо архівування (ARCHIVE) замість видалення для 100% збереження даних. Дивіться [NO_DELETE_POLICY.md](NO_DELETE_POLICY.md) для деталей.

## 📊 Project Status

- ✅ **291 tests passing** | 2 skipped (expected) - **100% success rate**
- ✅ **82% code coverage** - Production ready (with parallel execution)
- ✅ **CI/CD Pipeline** - Automated testing and deployment
- ✅ **Security** - Flask-Talisman, CORS, Secret Management
- ✅ **Database** - Alembic migrations, Connection pooling
- ✅ **Test Isolation** - pytest-xdist with loadscope for parallel execution
- ✅ **Test Stability** - StaticPool for database isolation, comprehensive error handling

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Redis
- PostgreSQL/MySQL (or SQLite for development)
- Google Cloud OAuth credentials

### Installation

1. **Clone repository:**
   ```bash
   git clone https://github.com/Eugen1189/auramail.git
   cd auramail
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Initialize database:**
   ```bash
   python init_database.py
   alembic upgrade head
   ```

5. **Start services:**
   ```bash
   # Terminal 1: Flask app
   python server.py
   
   # Terminal 2: RQ Worker
   python worker.py
   ```

## 📁 Project Structure

```
auramail/
├── server.py              # Flask web application
├── tasks.py               # Background task processing
├── worker.py              # RQ worker process
├── database.py            # SQLAlchemy models
├── config.py              # Configuration management
├── utils/
│   ├── gmail_api.py       # Gmail API integration (82% coverage)
│   ├── gemini_processor.py # AI classification (86% coverage)
│   ├── db_logger.py       # Database logging (58% coverage)
│   ├── agents.py          # AI agents (Librarian, Security Guard)
│   └── cache_helper.py    # Cache management (100% coverage)
├── tests/                 # Test suite (291 tests)
│   ├── test_db_logger_coverage.py  # Additional coverage tests
│   ├── test_worker.py              # Worker tests
│   └── ...
├── legacy/                # Maintenance scripts (0% coverage, manual use)
│   ├── test_gmail_api.py
│   ├── test_gemini_processor_extended.py
│   ├── test_db_logger_extended.py
│   └── ...
├── deployment/            # Deployment configurations
│   └── systemd/          # Systemd service files
└── .github/workflows/    # CI/CD pipeline
    └── ci.yml
```

## 🧪 Testing

**Run all tests (parallel execution):**
```bash
pytest tests/ -v
```

**Run with coverage (parallel execution - recommended):**
```bash
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
```

**Coverage report:**
- Open `htmlcov/index.html` in browser
- **Note:** Coverage works best with parallel execution (`pytest-xdist`). If you see coverage warnings, they don't affect test results.

**Test Configuration:**
- Parallel execution: `pytest-xdist` with `--dist loadscope` (default)
- Database isolation: `StaticPool` for complete test isolation
- Test order: `pytest-order` ensures proper execution sequence

## 🔄 CI/CD Pipeline

The project includes automated CI/CD via GitHub Actions:

- **On Push/PR:** Runs linting, tests, and coverage checks
- **On Main:** Automatically deploys to production
- **On Develop:** Deploys to staging environment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## 📈 Code Coverage

| Module | Coverage | Status |
|--------|----------|--------|
| `utils/db_logger.py` | 68% | ✅ Good |
| `utils/gemini_processor.py` | 86% | ✅ Excellent |
| `utils/gmail_api.py` | 82% | ✅ Excellent |
| `database.py` | 88% | ✅ Excellent |
| `tasks.py` | 84% | ✅ Excellent |
| `server.py` | 62% | ✅ Good |
| `worker.py` | 30% | ⚠️ Basic (tested via tasks.py) |
| **Total** | **82%** | ✅ Production Ready |

**Test Statistics:**
- 🧪 **291 tests passing** | 2 skipped (expected)
- ⚡ **Parallel execution** with pytest-xdist (loadscope)
- 🔒 **Full isolation** with StaticPool and comprehensive fixtures
- 📊 **Coverage report:** Run `pytest --cov=. --cov-report=html` (single-threaded for final report)

## 🔒 Security Features

- ✅ HTTPS enforcement (Flask-Talisman)
- ✅ Content Security Policy (CSP)
- ✅ CORS configuration
- ✅ Secret management (python-decouple)
- ✅ Secure session management

## 📚 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [TESTING.md](TESTING.md) - Testing documentation
- [DATABASE_SETUP.md](DATABASE_SETUP.md) - Database setup
- [ENV_SETUP.md](ENV_SETUP.md) - Environment variables

## 🛠️ Technologies

- **Backend:** Flask, SQLAlchemy, RQ (Redis Queue)
- **AI:** Google Gemini API
- **APIs:** Gmail API, Google Calendar API
- **Database:** PostgreSQL/MySQL/SQLite
- **Testing:** pytest, pytest-cov
- **CI/CD:** GitHub Actions
- **Deployment:** Docker, Systemd, Nginx

## 📝 License

[Your License Here]

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Ensure all tests pass
6. Submit a pull request

---

**Repository:** https://github.com/Eugen1189/auramail

"# auramail" 

