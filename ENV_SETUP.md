# Environment Setup Guide

## Creating .env file

1. Create a `.env` file in the project root directory
2. Copy the configuration below and fill in your actual values

```bash
# AuraMail Configuration File
# IMPORTANT: Never commit .env file to Git! It contains secrets.

# ============================================
# CRITICAL SECURITY SETTINGS
# ============================================

# Flask Secret Key (REQUIRED for production)
# Generate a secure key using: python -c "import secrets; print(secrets.token_hex(32))"
FLASK_SECRET_KEY=CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_IN_PRODUCTION

# Base URI for OAuth callbacks
# Development: https://127.0.0.1:5000
# Production: https://your-domain.com
BASE_URI=https://127.0.0.1:5000

# Debug mode (MUST be False in production!)
DEBUG=False

# ============================================
# API KEYS
# ============================================

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Google OAuth Client Secrets File Path
GOOGLE_CLIENT_SECRETS_PATH=client_secret.json

# ============================================
# DATABASE & REDIS
# ============================================

# Redis URL for task queue
REDIS_URL=redis://localhost:6379/0

# Database URL
# SQLite (development): sqlite:///auramail.db
# PostgreSQL (production): postgresql://user:password@host:port/dbname
DATABASE_URL=sqlite:///auramail.db

# Database Connection Pool Settings (optional)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_RECYCLE=3600

# ============================================
# APPLICATION SETTINGS
# ============================================

MAX_MESSAGES_TO_PROCESS=50
TIMEZONE=Europe/Kyiv
LOG_FILE=auramail_log.json
PROGRESS_FILE=progress.json

# ============================================
# SECURITY SETTINGS
# ============================================

# CORS Origins (comma-separated list)
# Production: https://your-frontend-domain.com,https://www.your-frontend-domain.com
# Leave empty to disable CORS (most secure, if frontend is same domain)
CORS_ORIGINS=

# Allow all CORS origins (ONLY for development!)
ALLOW_ALL_CORS=False

# Force HTTPS redirects
FORCE_HTTPS=True
```

## Generating Secure Flask Secret Key

Run this command to generate a secure random key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as the value of `FLASK_SECRET_KEY` in your `.env` file.

## Security Notes

1. **NEVER commit `.env` file to Git** - it's already in `.gitignore`
2. **Change `FLASK_SECRET_KEY`** before deploying to production
3. **Set `DEBUG=False`** in production
4. **Set `ALLOW_ALL_CORS=False`** in production
5. **Configure `CORS_ORIGINS`** with your production frontend domain(s)
6. **Set `FORCE_HTTPS=True`** in production

## Installation

After creating `.env` file, install the new dependencies:

```bash
pip install -r requirements.txt
```

This will install:
- `python-decouple` - for secure configuration management
- `Flask-CORS` - for CORS protection
- `Flask-Talisman` - for HTTP security headers

