# Docker Deployment Guide - AuraMail

## Quick Start (One Command)

```bash
docker-compose up -d
```

This single command starts:
- **Flask Web Server** (port 5000)
- **Redis** (port 6379)
- **PostgreSQL Database** (port 5432)
- **RQ Worker** (background task processor)

## Prerequisites

1. **Docker** and **Docker Compose** installed
2. **Google OAuth Credentials** (`client_secret.json`)
3. **Environment Variables** (`.env` file)

## Setup

### 1. Copy Environment Template

```bash
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your values:

```bash
# Required
FLASK_SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-api-key

# Database (defaults work for docker-compose)
DB_USER=auramail
DB_PASSWORD=auramail_password
DB_NAME=auramail
```

### 3. Add Google OAuth Credentials

Place your `client_secret.json` file in the project root directory.

### 4. Start Services

```bash
# Development
docker-compose up -d

# Production (with resource limits)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Service Architecture

```
┌─────────────┐
│   Web App   │  Flask + Gunicorn (4 workers)
│  (Port 5000)│
└──────┬──────┘
       │
       ├───► Redis (Task Queue)
       │
       ├───► PostgreSQL (Database)
       │
       └───► Worker (Background Tasks)
```

## Services

### Web Server (`web`)
- **Image**: Built from `Dockerfile`
- **Port**: 5000 (configurable via `WEB_PORT`)
- **Command**: Gunicorn with 4 workers
- **Health Check**: `GET /health`

### Worker (`worker`)
- **Image**: Same as web (different command)
- **Command**: `python worker.py`
- **Purpose**: Processes background tasks (email sorting, voice search)

### Redis (`redis`)
- **Image**: `redis:7-alpine`
- **Port**: 6379 (configurable via `REDIS_PORT`)
- **Purpose**: Task queue and caching

### PostgreSQL (`db`)
- **Image**: `postgres:15-alpine`
- **Port**: 5432 (configurable via `DB_PORT`)
- **Purpose**: Application database

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | Flask session secret key | **Required** |
| `GEMINI_API_KEY` | Google Gemini API key | **Required** |
| `DATABASE_URL` | Database connection string | Auto-generated |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `DEBUG` | Enable debug mode | `False` |
| `BASE_URI` | Application base URL | `https://127.0.0.1:5000` |
| `DB_USER` | PostgreSQL username | `auramail` |
| `DB_PASSWORD` | PostgreSQL password | `auramail_password` |
| `DB_NAME` | PostgreSQL database name | `auramail` |

## Common Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f worker
```

### Restart Service
```bash
docker-compose restart web
docker-compose restart worker
```

### Execute Commands in Container
```bash
# Web container
docker-compose exec web bash

# Worker container
docker-compose exec worker bash

# Database
docker-compose exec db psql -U auramail -d auramail
```

### Database Migrations
```bash
docker-compose exec web alembic upgrade head
```

### Check Service Health
```bash
# Web health check
curl http://localhost:5000/health

# Redis
docker-compose exec redis redis-cli ping

# Database
docker-compose exec db pg_isready -U auramail
```

## Production Deployment

### 1. Use Production Override

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 2. Configure Reverse Proxy

Use Nginx or Traefik as reverse proxy:

```nginx
# Nginx example
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Set Production Environment Variables

```bash
# .env
DEBUG=False
FORCE_HTTPS=True
ALLOW_ALL_CORS=False
BASE_URI=https://your-domain.com
```

### 4. Resource Limits

Production override includes resource limits:
- **Web**: 2 CPU, 2GB RAM
- **Worker**: 2 CPU, 2GB RAM

Adjust in `docker-compose.prod.yml` based on your needs.

## Troubleshooting

### Services Won't Start

1. **Check logs**:
   ```bash
   docker-compose logs
   ```

2. **Verify environment variables**:
   ```bash
   docker-compose config
   ```

3. **Check port conflicts**:
   ```bash
   # Check if ports are in use
   netstat -tuln | grep -E '5000|6379|5432'
   ```

### Database Connection Errors

1. **Wait for database to be ready**:
   ```bash
   docker-compose up -d db
   # Wait 10 seconds
   docker-compose up -d web worker
   ```

2. **Check database logs**:
   ```bash
   docker-compose logs db
   ```

### Worker Not Processing Tasks

1. **Check worker logs**:
   ```bash
   docker-compose logs worker
   ```

2. **Verify Redis connection**:
   ```bash
   docker-compose exec worker python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.ping())"
   ```

### Health Check Failing

1. **Check web service**:
   ```bash
   curl http://localhost:5000/health
   ```

2. **Verify all dependencies**:
   - Redis is accessible
   - Database is accessible
   - Environment variables are set

## Scaling

### Scale Workers

```bash
docker-compose up -d --scale worker=3
```

This starts 3 worker instances for parallel task processing.

### Scale Web Servers

```bash
docker-compose up -d --scale web=2
```

**Note**: Use a load balancer (Nginx, Traefik) when scaling web servers.

## Data Persistence

Volumes are created automatically:
- `redis_data` - Redis persistence
- `postgres_data` - PostgreSQL data

To backup:
```bash
# Database backup
docker-compose exec db pg_dump -U auramail auramail > backup.sql

# Redis backup
docker-compose exec redis redis-cli SAVE
```

## White Label Deployment

This Docker setup is perfect for "White Label" deployment:

1. **One Command Start**: `docker-compose up -d`
2. **Isolated Services**: Each component in its own container
3. **Easy Configuration**: Environment variables via `.env`
4. **Production Ready**: Includes production override with resource limits
5. **Health Checks**: Built-in health monitoring
6. **Logging**: Centralized logging via Docker

## CI/CD Integration

The GitHub Actions workflow (`.github/workflows/ci.yml`) automatically:
- Runs all 291+ tests on every commit
- Generates coverage reports (83%+ coverage)
- Builds Docker images
- Validates Docker Compose configuration

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Verify configuration: `docker-compose config`
3. Test health endpoints: `curl http://localhost:5000/health`

