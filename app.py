import asyncio
import sys
import os
from aiohttp import web

# Ensure the import path is set correctly if running from the CLI
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import SettingsManager
from bot.telegram_bot import MediaBot
from utils.logger import logger

async def health_check(request):
    """Simple HTTP endpoint for cloud platform health checks."""
    return web.Response(text="Media Downloader Bot is fully online globally. 🟢")

async def main():
    logger.info("Initializing Standalone Media Downloader Bot for Cloud Deployment...")
    config = SettingsManager()
    
    token = config.get("bot_token")
    if not token or token == "YOUR_TOKEN_HERE" or token == "":
        logger.error("No valid bot_token found. Ensure you have populated your environment variables.")
        sys.exit(1)
        
    # Start the actual Telegram Bot Async
    bot = MediaBot(config)
    await bot.start_polling()
    
    # Cloud Deployment Web Server (Binds to $PORT to satisfy Railway/Render/Heroku healthchecks)
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    logger.info(f"Binding HTTP Dummy Health Check Server to Port {port}...")
    await site.start()
    
    logger.info("Standalone Bot successfully initialized. Listening to the internet.")
    
    # Keep the async loop alive indefinitely since start_polling() is non-blocking
    try:
        while bot.is_running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    finally:
        await bot.stop()
        await runner.cleanup()
        logger.info("Standalone Bot completely stopped.")

if __name__ == '__main__':
    # Cloud environments usually need aggressive flushing to not buffer logs
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in standalone runner: {e}")
        sys.exit(1)
