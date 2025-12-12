# AuraMail Deployment Guide

## Systemd Services

### Installation

1. Copy service files to systemd directory:
   ```bash
   sudo cp deployment/systemd/auramail-*.service /etc/systemd/system/
   ```

2. Create environment file:
   ```bash
   sudo mkdir -p /etc/auramail
   sudo nano /etc/auramail/auramail.env
   ```
   Add your environment variables:
   ```
   REDIS_URL=redis://localhost:6379/0
   DATABASE_URL=postgresql://user:password@localhost/auramail
   FLASK_SECRET_KEY=your-secret-key
   GEMINI_API_KEY=your-api-key
   DEBUG=False
   ```

3. Create application directory and user:
   ```bash
   sudo useradd -r -s /bin/false auramail
   sudo mkdir -p /opt/auramail /var/log/auramail
   sudo chown auramail:auramail /opt/auramail /var/log/auramail
   ```

4. Reload systemd and enable services:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable auramail-web.service
   sudo systemctl enable auramail-worker.service
   sudo systemctl start auramail-web.service
   sudo systemctl start auramail-worker.service
   ```

### Management

- Check status: `sudo systemctl status auramail-web` or `sudo systemctl status auramail-worker`
- View logs: `sudo journalctl -u auramail-web -f` or `sudo journalctl -u auramail-worker -f`
- Restart: `sudo systemctl restart auramail-web` or `sudo systemctl restart auramail-worker`
- Stop: `sudo systemctl stop auramail-web` or `sudo systemctl stop auramail-worker`

## Docker Deployment

See `docker-compose.yml` for containerized deployment.

```bash
docker-compose up -d
```

## Nginx Configuration

Example Nginx reverse proxy configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

