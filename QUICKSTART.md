# QUICK START - Secure Deployment

## ⚡ 5-Minute Setup

### Step 1: Prepare Environment

```bash
cd super_media_dl_bot

# Create .env file
cp .env.example .env

# Edit with your settings
nano .env
```

### Step 2: Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### Step 3: Run Bot

```bash
python3 run_bot.py
```

**Expected Output**:

```
============================================================
Initializing Standalone Media Downloader Bot...
============================================================
Database initialized: history.db
Bot token configured: 8792...****
Starting bot polling...
Standalone Bot successfully initialized. Press Ctrl+C to stop.
============================================================
```

Stop with `Ctrl+C` when done testing.

---

## 🔑 Required Configuration

### Get Bot Token

1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Follow prompts to get your token

### Get Admin ID

1. Search for `@userinfobot`
2. Send any message
3. Copy your numeric ID

### Update .env

```env
BOT_TOKEN=<your_token_from_botfather>
ADMIN_IDS=<your_numeric_id>
```

---

## 🌐 Deploy to VPS (Ubuntu)

```bash
# SSH into server
ssh user@your_vps_ip

# Install system packages
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git

# Clone repo
git clone <your-repo> super_media_dl_bot
cd super_media_dl_bot

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_headless.txt

# Configure
cp .env.example .env
nano .env  # Add BOT_TOKEN and ADMIN_IDS

# Test
python3 run_bot.py  # Press Ctrl+C after confirming it works

# Install as service
sudo cp media_bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/media_bot.service  # Update paths if needed
sudo systemctl daemon-reload
sudo systemctl enable media_bot.service
sudo systemctl start media_bot.service

# Check status
sudo systemctl status media_bot.service
sudo journalctl -u media_bot.service -f
```

---

## 🐳 Deploy with Docker

```bash
# Prepare
cp .env.example .env
nano .env  # Add BOT_TOKEN

# Run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## ✅ Verification

Send these to your bot on Telegram:

```
/start     → Bot responds with welcome message
/help      → Bot shows instructions
/stats     → Shows statistics (only works if you're admin)
```

---

## 🆘 Troubleshooting

### Bot won't start

```bash
python3 run_bot.py
# Check error message
# Most common: BOT_TOKEN not set in .env
```

### Database problems

```bash
# Check if database exists
ls -la history.db

# Reinitialize if corrupted
rm history.db
python3 run_bot.py  # Creates new database
```

### ffmpeg not found

```bash
# Install ffmpeg
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
# Windows: Download from ffmpeg.org
```

---

## 📚 Full Documentation

- **Deployment**: See `DEPLOYMENT_GUIDE.md`
- **Security**: See `SECURITY_FIXES.md`
- **Original README**: See `README.md`

---

**Status**: ✅ Production Ready  
**Last Updated**: March 18, 2026
