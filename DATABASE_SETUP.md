# Database Setup Guide for AuraMail

## Overview

AuraMail now uses SQLAlchemy with connection pooling instead of JSON files for data storage:
- `auramail_log.json` → `action_logs` table
- `progress.json` → `progress` table  
- `last_report.json` → `reports` table

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure database URL in `.env`:**
   ```env
   # For SQLite (development):
   DATABASE_URL=sqlite:///auramail.db
   
   # For PostgreSQL (production):
   DATABASE_URL=postgresql://user:password@host:port/dbname
   ```

3. **Optional: Configure connection pool (in `.env`):**
   ```env
   DB_POOL_SIZE=10           # Max persistent connections
   DB_MAX_OVERFLOW=5         # Additional connections during peak
   DB_POOL_RECYCLE=3600      # Recycle connections every hour
   ```

## Database Initialization

### Option 1: Simple initialization (creates tables)

```bash
python init_database.py
```

### Option 2: Using Alembic (recommended for production)

1. **Initialize Alembic (already done - `alembic/` folder exists):**

2. **Generate initial migration:**
   ```bash
   alembic revision --autogenerate -m "Initial schema setup"
   ```

3. **Apply migrations:**
   ```bash
   alembic upgrade head
   ```

## Creating New Migrations

Whenever you change database models in `database.py`:

1. **Generate migration:**
   ```bash
   alembic revision --autogenerate -m "Description of changes"
   ```

2. **Review the generated migration file** in `alembic/versions/`

3. **Apply migration:**
   ```bash
   alembic upgrade head
   ```

4. **Rollback if needed:**
   ```bash
   alembic downgrade -1  # Rollback one version
   ```

## Migration Commands

- `alembic current` - Show current database version
- `alembic history` - Show migration history
- `alembic upgrade head` - Apply all pending migrations
- `alembic downgrade base` - Rollback all migrations
- `alembic upgrade +1` - Upgrade one version
- `alembic downgrade -1` - Downgrade one version

## Connection Pooling

The database is configured with connection pooling:
- **pool_size**: Maximum number of persistent connections (default: 10)
- **max_overflow**: Additional connections during peak load (default: 5)
- **pool_recycle**: Recycle connections every N seconds (default: 3600)
- **pool_pre_ping**: Verify connections before using (enabled)

This ensures that your 8-thread worker can efficiently share database connections without creating new ones for each thread.

## Database Models

### ActionLog
Stores email processing logs:
- `msg_id` (unique, indexed)
- `timestamp` (indexed)
- `subject`, `ai_category`, `action_taken`
- `details` (JSON field for full classification data)

### Progress
Stores current processing progress:
- Only one record at a time
- `total`, `current`, `status`, `details`
- `stats` (JSON field)

### Report
Stores sorting job reports:
- `created_at` (indexed)
- Statistics: `total_processed`, `important`, `deleted`, etc.
- `stats` (JSON field for full statistics)

## Production Notes

1. **Use PostgreSQL** instead of SQLite for production
2. **Backup database regularly**
3. **Monitor connection pool usage**
4. **Run migrations** before deploying new code
5. **Test migrations** on staging first

