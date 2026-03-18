# 🚀 PRE-DEPLOYMENT CHECKLIST

Use this checklist to verify your bot is ready for production deployment.

---

## Phase 1: Security Review ✅

- [ ] Reviewed SECURITY_FIXES.md
- [ ] Verified token removed from config.json
- [ ] Confirmed .gitignore created
- [ ] Checked .env.example exists
- [ ] Verified all 10 security fixes are in place

---

## Phase 2: Local Environment Setup ✅

- [ ] Python 3.8+ installed

  ```bash
  python3 --version
  ```

- [ ] ffmpeg installed

  ```bash
  ffmpeg -version
  ```

- [ ] Virtual environment created

  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

- [ ] Dependencies installed

  ```bash
  pip install -r requirements.txt
  ```

- [ ] python-dotenv installed
  ```bash
  pip list | grep python-dotenv
  ```

---

## Phase 3: Configuration Setup ✅

- [ ] .env file created from template

  ```bash
  cp .env.example .env
  ```

- [ ] Got bot token from @BotFather
- [ ] Got admin ID from @userinfobot
- [ ] Updated .env with:

  ```env
  BOT_TOKEN=your_token_here
  ADMIN_IDS=your_id_here
  ```

- [ ] Verified .env is not in git
  ```bash
  git status | grep -q ".env" && echo "⚠️ .env in git!" || echo "✅ .env safe"
  ```

---

## Phase 4: Code Validation ✅

- [ ] Configuration loads without errors

  ```bash
  python3 -c "from config.settings import SettingsManager; c = SettingsManager(); print('✅ OK' if not c.validate() else c.validate())"
  ```

- [ ] Database initializes

  ```bash
  python3 -c "from utils.database import init_db; init_db(); print('✅ Database OK')"
  ```

- [ ] URL validation works

  ```bash
  python3 -c "from downloader.ytdlp_handler import YTDownloader; print('✅ Valid URL' if YTDownloader.is_url_valid('https://youtube.com/watch?v=test') else '❌ Invalid')"
  ```

- [ ] Logger initializes
  ```bash
  python3 -c "from utils.logger import logger; logger.info('✅ Logger OK'); print('Check logs/app.log')"
  ```

---

## Phase 5: Local Testing ✅

- [ ] Bot starts without errors

  ```bash
  timeout 5 python3 run_bot.py || true
  ```

  Should show:

  ```
  Initializing Standalone Media Downloader Bot...
  Database initialized: history.db
  Bot token configured: 8792...****
  ```

- [ ] No secrets in logs

  ```bash
  cat logs/app.log | grep -i "token" || echo "✅ No token in logs"
  ```

- [ ] Logs directory created

  ```bash
  ls -la logs/app.log
  ```

- [ ] Database file created
  ```bash
  ls -la history.db
  ```

---

## Phase 6: Telegram Bot Testing ✅

- [ ] Send `/start` to bot
  - [ ] Receives welcome message

- [ ] Send `/help` to bot
  - [ ] Receives instructions

- [ ] Send `/stats` to bot (as admin)
  - [ ] Shows statistics

- [ ] Send `/users` to bot (as admin)
  - [ ] Shows recent users

- [ ] Send `/health` to bot (as admin)
  - [ ] Shows health status

- [ ] Test with invalid user
  - [ ] Receives "no permissions" message

---

## Phase 7: File Operations Testing ✅

- [ ] Test URL validation
  - [ ] YouTube URL accepted
  - [ ] TikTok URL accepted
  - [ ] Random domain rejected (⚠️ requires sending in Telegram)

- [ ] Verify downloads directory created

  ```bash
  ls -la downloads/
  ```

- [ ] Verify file cleanup works (check after test download)
  ```bash
  ls downloads/*/  # Should be relatively clean
  ```

---

## Phase 8: Database Testing ✅

- [ ] Database queries work

  ```bash
  python3 -c "from utils.database import get_stats; dl, users = get_stats(); print(f'✅ DB OK: {dl} downloads, {users} users')"
  ```

- [ ] Rate limiting works
  ```bash
  python3 -c "from utils.database import check_rate_limit; allowed, _ = check_rate_limit(123, 'test', 5); print('✅ Rate limit OK' if allowed else 'Rate limited')"
  ```

---

## Phase 9: Security Verification ✅

- [ ] No secrets in environment

  ```bash
  env | grep -i token || echo "✅ No token in environment"
  ```

- [ ] .env not in git

  ```bash
  git ls-files | grep ".env" || echo "✅ .env not tracked"
  ```

- [ ] config.json token is empty

  ```bash
  python3 -c "import json; c=json.load(open('config/config.json')); print('✅ Empty token' if not c.get('bot_token') else '⚠️ Token in file')"
  ```

- [ ] .gitignore is comprehensive
  ```bash
  grep -q "\.env" .gitignore && echo "✅ .gitignore complete" || echo "⚠️ Missing .env"
  ```

---

## Phase 10: Documentation ✅

- [ ] Read QUICKSTART.md

  ```bash
  cat QUICKSTART.md | head -20
  ```

- [ ] Read DEPLOYMENT_GUIDE.md

  ```bash
  cat DEPLOYMENT_GUIDE.md | head -30
  ```

- [ ] Read SECURITY_FIXES.md

  ```bash
  cat SECURITY_FIXES.md | head -30
  ```

- [ ] Read this checklist (you are here)

---

## Phase 11: Production Deployment ✅

### For Local Running

- [ ] Can start with: `python3 run_bot.py`
- [ ] Can stop with: `Ctrl+C`

### For VPS Deployment

- [ ] systemd service file ready
- [ ] Service file paths updated
- [ ] Can enable with: `sudo systemctl enable media-bot.service`
- [ ] Can start with: `sudo systemctl start media-bot.service`
- [ ] Can check logs: `sudo journalctl -u media-bot.service -f`

### For Docker Deployment

- [ ] Dockerfile exists
- [ ] docker-compose.yml exists
- [ ] Can build with: `docker-compose build`
- [ ] Can start with: `docker-compose up -d`
- [ ] Can check logs: `docker-compose logs -f`

---

## Phase 12: Monitoring Setup ✅

- [ ] Logs directory monitored

  ```bash
  tail -f logs/app.log
  ```

- [ ] Database backups scheduled (production only)

  ```bash
  cp history.db history.db.backup.$(date +%Y%m%d)
  ```

- [ ] Disk space monitored

  ```bash
  du -sh downloads/ logs/
  ```

- [ ] Admin commands tested and working

---

## Final Verification ✅

Run this complete health check:

```bash
#!/bin/bash
echo "🔍 Running complete health check..."
echo ""

echo "1. Configuration:"
python3 -c "from config.settings import SettingsManager; c = SettingsManager(); errors = c.validate(); print('✅ PASS' if not errors else '❌ FAIL: ' + str(errors))" || echo "❌ FAIL"

echo ""
echo "2. Database:"
python3 -c "from utils.database import init_db; init_db(); print('✅ PASS')" || echo "❌ FAIL"

echo ""
echo "3. URL Validation:"
python3 -c "from downloader.ytdlp_handler import YTDownloader; r = YTDownloader.is_url_valid('https://youtube.com/test'); print('✅ PASS' if r else '❌ FAIL')" || echo "❌ FAIL"

echo ""
echo "4. Logging:"
test -f logs/app.log && echo "✅ PASS" || echo "❌ FAIL"

echo ""
echo "5. Security (.env not in git):"
git ls-files | grep -q ".env" && echo "❌ FAIL: .env in git" || echo "✅ PASS"

echo ""
echo "6. Secrets (no token in file):"
python3 -c "import json; c=json.load(open('config/config.json')); print('✅ PASS' if not c.get('bot_token') else '❌ FAIL')" || echo "❌ FAIL"

echo ""
echo "🎉 All checks completed!"
```

---

## ✅ Deployment Approved If

- [ ] All boxes checked in this list
- [ ] All phases completed successfully
- [ ] Health check shows all PASS
- [ ] No errors in logs
- [ ] Bot responds to Telegram messages
- [ ] Admin commands work
- [ ] No secrets in git

---

## 🚀 Ready to Deploy!

Once all checks pass, you can:

1. **Local**: `python3 run_bot.py`
2. **VPS**: Follow DEPLOYMENT_GUIDE.md → VPS section
3. **Docker**: Follow DEPLOYMENT_GUIDE.md → Docker section

---

## 📞 Troubleshooting

If any check fails:

1. Review the error message carefully
2. Check the relevant section in DEPLOYMENT_GUIDE.md
3. Check logs: `tail -50 logs/app.log`
4. Review SECURITY_FIXES.md for context
5. Try the command manually for more details

---

**Remember**: ✅ Pass all checks before deploying!

**Status**: Ready for deployment  
**Date**: March 18, 2026
