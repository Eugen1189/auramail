# 🚀 AuraMail Deployment Guide

## CI/CD Pipeline Overview

The project uses GitHub Actions for automated testing and deployment.

## Workflow

1. **Build and Test** - Runs on every push and pull request
   - Linting with flake8
   - Running 60+ tests with pytest
   - Coverage reporting (target: 50%+)
   - Building Docker images

2. **Deploy to Production** - Runs only on push to `main` branch
   - Pulls latest code
   - Runs database migrations
   - Restarts systemd services

3. **Deploy to Staging** - Runs only on push to `develop` branch
   - Similar to production, but on staging environment

## Required GitHub Secrets

### For Testing (Optional)
- `GEMINI_API_KEY_TEST` - Test API key for CI tests (optional, defaults to 'test_key')

### For Production Deployment
- `PROD_HOST` - Production server hostname or IP
- `PROD_USERNAME` - SSH username for production server
- `PROD_SSH_KEY` - Private SSH key for production server
- `PROD_SSH_PORT` - SSH port (optional, defaults to 22)

### For Staging Deployment (Optional)
- `STAGING_HOST` - Staging server hostname or IP
- `STAGING_USERNAME` - SSH username for staging server
- `STAGING_SSH_KEY` - Private SSH key for staging server
- `STAGING_SSH_PORT` - SSH port (optional, defaults to 22)

## Setting Up GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the appropriate value

## Production Server Setup

### Prerequisites

1. **Server Requirements:**
   - Ubuntu 20.04+ or similar Linux distribution
   - Python 3.11+
   - PostgreSQL or MySQL (recommended)
   - Redis
   - Nginx
   - Systemd

2. **Directory Structure:**
   ```bash
   /var/www/auramail/
   ├── app/
   ├── alembic/
   ├── requirements.txt
   ├── .env
   └── ...
   ```

3. **Systemd Services:**
   - `auramail-web.service` - Flask/Gunicorn web application
   - `auramail-worker.service` - RQ worker

### Deployment Steps

1. **Clone Repository:**
   ```bash
   cd /var/www
   git clone https://github.com/yourusername/auramail.git
   cd auramail
   ```

2. **Set Up Virtual Environment:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env with production values
   nano .env
   ```

4. **Set Up Database:**
   ```bash
   # Initialize database
   python init_database.py
   
   # Run migrations
   alembic upgrade head
   ```

5. **Configure Systemd Services:**
   ```bash
   # Copy service files
   sudo cp deployment/systemd/auramail-web.service /etc/systemd/system/
   sudo cp deployment/systemd/auramail-worker.service /etc/systemd/system/
   
   # Edit paths in service files if needed
   sudo nano /etc/systemd/system/auramail-web.service
   sudo nano /etc/systemd/system/auramail-worker.service
   
   # Reload systemd and start services
   sudo systemctl daemon-reload
   sudo systemctl enable auramail-web.service
   sudo systemctl enable auramail-worker.service
   sudo systemctl start auramail-web.service
   sudo systemctl start auramail-worker.service
   ```

6. **Configure Nginx:**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Manual Deployment

If you need to deploy manually:

```bash
cd /var/www/auramail
git pull origin main
source venv/bin/activate  # if using venv
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart auramail-web.service
sudo systemctl restart auramail-worker.service
```

## Monitoring

Check service status:
```bash
sudo systemctl status auramail-web.service
sudo systemctl status auramail-worker.service
```

View logs:
```bash
sudo journalctl -u auramail-web.service -f
sudo journalctl -u auramail-worker.service -f
```

## Troubleshooting

1. **Tests failing in CI:**
   - Check coverage reports in GitHub Actions artifacts
   - Review test logs for specific failures

2. **Deployment fails:**
   - Verify SSH keys and permissions
   - Check server directory paths
   - Review systemd service configurations

3. **Services not starting:**
   - Check logs: `journalctl -u auramail-web.service`
   - Verify .env file exists and has correct values
   - Ensure database is accessible

