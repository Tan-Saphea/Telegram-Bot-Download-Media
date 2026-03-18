# Media Downloader Bot - Telegram

A high-performance standalone Telegram bot allowing users to seamlessly download media (Videos & Audio) from platforms like **YouTube**, **TikTok**, and **Facebook** simply by sending a link to the bot!

Features:
- **Headless Mode** for 24/7 VPS integration (`run_bot.py`).
- **Optional Local Admin GUI** to view stats locally and tweak configs (`main.py`).
- **Database Tracking** with integrated sqlite3 spam-limits and usage stats.
- **Auto format fetching** with dynamic inline bot keyboards representing all available resolutions and fast audio MP3 conversion natively using ffmpeg.

---

## ⚡ Deployment on Ubuntu VPS (24/7 Setup)

This bot is entirely production-ready. You do not need the GUI (PyQt5) to run it online 24/7. Follow these steps to host it on an **Ubuntu Linux VPS**:

### 1. Install System Dependencies
First, install Python, PIP, virtual environment tools, and `ffmpeg` which handles all media processing securely on the back-end.
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git
```

### 2. Clone and Setup VENV
```bash
git clone https://your-repository-link.git super_media_dl_bot
cd super_media_dl_bot

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install headless requirements (skips heavy GUI packages)
pip install -r requirements_headless.txt
```

### 3. Add Your Bot Token
1. Get a token via Telegram's **@BotFather**.
2. Run the bot once to auto-generate the `config/config.json` folder or create it manually:
```bash
mkdir -p config
nano config/config.json
```
3. Ensure it looks like this:
```json
{
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE",
    "download_path": "downloads/",
    "ffmpeg_path": "",
    "max_file_size": 50.0
}
```

### 4. Test it!
```bash
python3 run_bot.py
```
*(Stop it with `Ctrl+C` once you confirm it works natively).*

### 5. Keep it online forever (SystemD Service)
To make your bot start exactly when your server does and auto-restart if it crashes:

1. Edit the provided template service file:
```bash
sudo nano media_bot.service
```
2. Adjust `User=` and `WorkingDirectory=` inside the `.service` file to match your exact Ubuntu location.
3. Move it to your `/etc/systemd` path:
```bash
sudo mv media_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
```
4. Enable and spin up your bot:
```bash
sudo systemctl enable media_bot.service
sudo systemctl start media_bot.service
```
5. **View Logs 🔴 Check status securely:**
```bash
sudo systemctl status media_bot.service
journalctl -u media_bot.service -f
```

---

## 🔥 Optional: Run locally with GUI Dashboard (macOS/Windows)

If you strictly want to run the Bot on your personal Computer occasionally with a polished Graphical Interface instead of headless:

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
