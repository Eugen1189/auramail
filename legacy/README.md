# Legacy Scripts

This directory contains maintenance and diagnostic scripts that are used manually for system administration and troubleshooting.

## Scripts Overview

These scripts have **0% test coverage** as they are:
- Used manually for diagnostics
- Not part of the main application flow
- Run on-demand by administrators

### Available Scripts

- **`check_database.py`** - Database connection and health checks
- **`check_db_locks.py`** - Database lock diagnostics
- **`check_oauth_scopes.py`** - OAuth scope verification
- **`check_redis.py`** - Redis connection checks
- **`clear_queue_simple.py`** - Simple queue clearing utility
- **`clear_redis_queue.py`** - Redis queue management
- **`commit_changes.py`** - Database commit utility
- **`create_env.py`** - Environment file creation helper
- **`fix_env.py`** - Environment file repair utility
- **`init_database.py`** - Database initialization (moved to legacy, use Alembic instead)
- **`scheduler.py`** - Legacy scheduler (use systemd/cron instead)
- **`scheduler_daily_followup.py`** - Legacy followup scheduler

## Usage

These scripts are **not included in test coverage** and should be:
- Used only by system administrators
- Run manually when needed
- Not executed as part of automated workflows

## Migration Notes

- **Database initialization:** Use `alembic upgrade head` instead of `init_database.py`
- **Scheduling:** Use systemd services or cron jobs instead of scheduler scripts
- **Queue management:** Use RQ dashboard or Redis CLI for queue operations

