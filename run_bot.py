import asyncio
import sys
import os

# Ensure the import path is set correctly if running from the CLI
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import SettingsManager
from bot.telegram_bot import MediaBot
from utils.logger import logger

async def main():
    logger.info("Initializing Standalone Media Downloader Bot...")
    config = SettingsManager()
    
    token = config.get("bot_token")
    if not token or token == "YOUR_TOKEN_HERE" or token == "":
        logger.error("No valid bot_token found in config/config.json. Please add it and restart.")
        sys.exit(1)
        
    bot = MediaBot(config)
    await bot.start_polling()
    
    logger.info("Standalone Bot successfully initialized. Press Ctrl+C to stop.")
    
    # Keep the async loop alive indefinitely since start_polling() is non-blocking
    try:
        while bot.is_running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        logger.info("Shutdown signal received (KeyboardInterrupt).")
    finally:
        await bot.stop()
        logger.info("Standalone Bot completely stopped.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in standalone runner: {e}")
        sys.exit(1)
