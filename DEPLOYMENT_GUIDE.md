# Secure Deployment Guide - Media Downloader Bot

## ⚠️ CRITICAL SECURITY FIXES APPLIED

This guide covers the security-hardened deployment process for your Telegram bot.

### Security Issues Fixed:

✅ **Bot token** - Removed from repository, uses environment variables  
✅ **Configuration** - Supports secure .env file management  
✅ **Input validation** - URL whitelist for supported platforms  
✅ **Path traversal** - Prevented with directory boundary checks  
✅ **File cleanup** - Automatic deletion of downloaded files  
✅ **Rate limiting** - Configurable per-minute limits  
✅ **Database** - Configurable path, proper error handling  
✅ **Logging** - Security event tracking for admin operations

---

## 1. LOCAL SETUP (Development/Testing)

### Prerequisites

- Python 3.8+
- ffmpeg installed (`brew install ffmpeg` on macOS, `apt install ffmpeg` on Linux)
- Virtual environment support

### Steps

```bash
# Clone the repository
cd super_media_dl_bot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### Configure .env

```env
# CRITICAL: Get token from @BotFather on Telegram
BOT_TOKEN=your_telegram_bot_token_here

# Paths
DOWNLOAD_PATH=downloads/
LOG_DIR=logs/
DATABASE_PATH=history.db

# Admin IDs (comma-separated, get from @userinfobot)
ADMIN_IDS=123456789,987654321

# Settings
MAX_FILE_SIZE_MB=50
RATE_LIMIT_PER_MINUTE=5
ENABLE_SSL_VERIFY=true
```

### Run Bot

```bash
python3 run_bot.py
```

Expected output:

```
============================================================
Initializing Standalone Media Downloader Bot...
============================================================
Database initialized: history.db
Bot token configured: 8792...****
Starting bot polling...
Standalone Bot successfully initialized. Press Ctrl+C to stop.
```

---

## 2. VPS DEPLOYMENT (Ubuntu/Debian)

### Prerequisites

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git
```

### Setup

```bash
# Create dedicated user (recommended)
sudo useradd -m -s /bin/bash mediabot
sudo su - mediabot

# Clone repository
git clone <your-repo-url> super_media_dl_bot
cd super_media_dl_bot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements_headless.txt

# Create .env file (NEVER commit this!)
cp .env.example .env
nano .env  # Add your BOT_TOKEN and settings
```

### Test Run

```bash
python3 run_bot.py
# Press Ctrl+C after confirming it starts successfully
```

### Setup SystemD Service

```bash
# Create service file
sudo nano /etc/systemd/system/media-bot.service
```

**Service file content:**

```ini
[Unit]
Description=Telegram Media Downloader Bot
After=network.target

[Service]
Type=simple
User=mediabot
WorkingDirectory=/home/mediabot/super_media_dl_bot
Environment="PATH=/home/mediabot/super_media_dl_bot/.venv/bin"
EnvironmentFile=/home/mediabot/super_media_dl_bot/.env
ExecStart=/home/mediabot/super_media_dl_bot/.venv/bin/python3 run_bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable media-bot.service
sudo systemctl start media-bot.service

# Check status
sudo systemctl status media-bot.service

# View logs
sudo journalctl -u media-bot.service -f
```

---

## 3. DOCKER DEPLOYMENT (Recommended)

### Create Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements_headless.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_headless.txt

# Copy application
COPY . .

# Create logs and downloads directories
RUN mkdir -p logs downloads

# Run bot
CMD ["python3", "run_bot.py"]
```

### Create docker-compose.yml

```yaml
version: "3.8"

services:
  media-bot:
    build: .
    container_name: telegram-media-bot
    restart: unless-stopped
    environment:
      BOT_TOKEN: ${BOT_TOKEN}
      DOWNLOAD_PATH: /app/downloads/
      LOG_DIR: /app/logs/
      DATABASE_PATH: /app/data/history.db
      ADMIN_IDS: ${ADMIN_IDS}
      MAX_FILE_SIZE_MB: ${MAX_FILE_SIZE_MB:-50}
      RATE_LIMIT_PER_MINUTE: ${RATE_LIMIT_PER_MINUTE:-5}
    volumes:
      - ./downloads:/app/downloads
      - ./logs:/app/logs
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Deploy with Docker

```bash
# Create .env file
cp .env.example .env
nano .env

# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop bot
docker-compose down
```

---

## 4. DATABASE & FILE MANAGEMENT

### Database Initialization

The database automatically initializes on first run with:

- `downloads` table - tracks all downloads
- `users` table - tracks user activity and rate limits
- Proper indexes for performance

### File Cleanup Strategy

- Downloads are automatically **deleted after upload** to Telegram
- Database records remain for statistics
- Configure `DOWNLOAD_PATH` to use external storage on VPS

### Disk Space Management

```bash
# Monitor disk usage
du -sh downloads/ logs/

# Clean old logs (keep last 7 days)
find logs/ -name "*.log" -mtime +7 -delete

# Database cleanup (optional)
sqlite3 history.db "DELETE FROM downloads WHERE download_date < date('now', '-30 days');"
```

---

## 5. SECURITY BEST PRACTICES

### .gitignore Compliance

The following are **never** committed:

- `.env` files (bot token)
- `config/config.json` (if contains token)
- `history.db` (user data)
- `downloads/` (media files)
- `logs/` (sensitive logs)

### Environment Variables

```bash
# NEVER do this (exposes token):
BOT_TOKEN='8792...xxx' python3 run_bot.py

# ALWAYS use .env:
source .env
python3 run_bot.py
```

### Bot Token Security

- Get token from **@BotFather** on Telegram (not shared)
- Store ONLY in `.env` file
- Rotate token if compromised
- Never share in logs or error messages

### Admin Access

```bash
# Verify admin IDs with @userinfobot
ADMIN_IDS=123456789,987654321
```

### API Rate Limiting

Default: 5 requests/minute per user

```env
RATE_LIMIT_PER_MINUTE=5
```

### File Size Limits

Default: 50MB (Telegram free tier limit)

```env
MAX_FILE_SIZE_MB=50
```

---

## 6. TROUBLESHOOTING

### Bot doesn't start

```bash
# Check configuration
python3 -c "from config.settings import SettingsManager; c = SettingsManager(); print(c.validate())"

# Check logs
tail -f logs/app.log
```

### Rate limited by Telegram

- Reduce `RATE_LIMIT_PER_MINUTE`
- Implement longer cooldowns
- Check admin operations logging

### Download failures

```bash
# Verify ffmpeg installation
which ffmpeg

# Check file permissions
ls -la downloads/

# View detailed logs
tail -50 logs/app.log | grep "Download failed"
```

### Database corruption

```bash
# Backup and reinitialize
cp history.db history.db.backup
rm history.db
python3 run_bot.py  # Reinitializes on startup
```

### Memory leaks

```bash
# Monitor memory usage
watch -n 5 'ps aux | grep python3'

# Check for uncleaned files
ls -lR downloads/ | wc -l
```

---

## 7. MONITORING & LOGS

### Log locations

- **Application logs**: `logs/app.log`
- **SystemD logs**: `journalctl -u media-bot.service`
- **Docker logs**: `docker-compose logs`

### Important log queries

```bash
# Check for admin operations
grep "admin" logs/app.log

# Check download errors
grep "Download failed" logs/app.log

# Check rate limiting
grep "Rate limit" logs/app.log

# Monitor startup
tail -20 logs/app.log
```

### Admin Commands

- `/stats` - Download statistics (admin only)
- `/users` - Recent users (admin only)
- `/health` - Bot health check (admin only)
- `/start` - Bot information
- `/help` - Usage instructions

---

## 8. PRODUCTION CHECKLIST

Before going live:

- [ ] Generated `.env` file from `.env.example`
- [ ] Bot token added to `.env` (NOT in config.json)
- [ ] Admin IDs configured in `.env`
- [ ] ffmpeg installed and PATH set
- [ ] Database initialized successfully
- [ ] Logs directory created and writable
- [ ] Downloads directory has sufficient disk space
- [ ] Rate limiting configured appropriately
- [ ] SSL verification enabled (default)
- [ ] .gitignore verified (no secrets in git)
- [ ] SystemD service or Docker setup complete
- [ ] Health check command works
- [ ] Monitored logs for 24 hours

---

## 9. UPGRADING & MAINTENANCE

### Update dependencies

```bash
source .venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Backup database

```bash
cp history.db history.db.backup.$(date +%Y%m%d)
```

### View statistics

```bash
# Via Telegram (admin only)
/stats

# Via database
sqlite3 history.db "SELECT COUNT(*) as downloads FROM downloads;"
sqlite3 history.db "SELECT COUNT(*) as users FROM users;"
```

---

## 10. SUPPORT & ISSUES

For issues:

1. Check logs: `tail -100 logs/app.log`
2. Verify configuration: `python3 -c "from config.settings import SettingsManager; c = SettingsManager(); errors = c.validate(); print(errors if errors else 'OK')"`
3. Test connectivity: Check internet connection and Telegram API availability
4. Review GitHub issues or create a new one with logs

---

**Last Updated**: March 18, 2026  
**Version**: Secure Hardened Edition
