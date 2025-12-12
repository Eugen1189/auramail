# 🤖 AuraMail - AI-Powered Email Organizer

**Production-ready email management system with AI classification, automated sorting, and comprehensive test coverage.**

## 📊 Project Status

- ✅ **60 tests** - All passing (100%)
- ✅ **66% code coverage** - Production ready
- ✅ **CI/CD Pipeline** - Automated testing and deployment
- ✅ **Security** - Flask-Talisman, CORS, Secret Management
- ✅ **Database** - Alembic migrations, Connection pooling

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
│   ├── gmail_api.py       # Gmail API integration (66% coverage)
│   ├── gemini_processor.py # AI classification (74% coverage)
│   ├── db_logger.py       # Database logging (75% coverage)
│   └── cache_helper.py    # Cache management
├── tests/                 # Test suite (60 tests)
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

Run all tests:
```bash
pytest tests/ -v --cov=. --cov-report=html
```

Coverage report:
- Open `htmlcov/index.html` in browser

## 🔄 CI/CD Pipeline

The project includes automated CI/CD via GitHub Actions:

- **On Push/PR:** Runs linting, tests, and coverage checks
- **On Main:** Automatically deploys to production
- **On Develop:** Deploys to staging environment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## 📈 Code Coverage

| Module | Coverage | Status |
|--------|----------|--------|
| `utils/db_logger.py` | 75% | ✅ Excellent |
| `utils/gemini_processor.py` | 74% | ✅ Excellent |
| `utils/gmail_api.py` | 66% | ✅ Good |
| `database.py` | 95% | ✅ Excellent |
| **Total** | **66%** | ✅ Production Ready |

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
