import asyncio
import sys
import os

# Ensure the import path is set correctly if running from the CLI
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import SettingsManager
from bot.telegram_bot import MediaBot
from utils.logger import logger
from utils.database import init_db, set_db_path

async def main():
    logger.info("=" * 60)
    logger.info("Initializing Standalone Media Downloader Bot...")
    logger.info("=" * 60)
    
    # Load configuration
    config = SettingsManager()
    
    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("\nPlease set BOT_TOKEN via environment variable:")
        logger.error("  export BOT_TOKEN='your_token_here'")
        logger.error("\nOr update config/config.json with your settings.")
        sys.exit(1)
    
    # Set up database path from config
    db_path = config.get("database_path", "history.db")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    set_db_path(db_path)
    
    # Initialize database
    try:
        init_db()
        logger.info(f"Database initialized: {db_path}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)
    
    # Initialize bot
    token = config.get("bot_token")
    masked_token = f"{token[:4]}...{token[-4:]}" if len(token) > 10 else "***"
    logger.info(f"Bot token configured: {masked_token}")
    
    bot = MediaBot(config)
    
    logger.info("Starting bot polling...")
    await bot.start_polling()
    
    logger.info("Standalone Bot successfully initialized. Press Ctrl+C to stop.")
    logger.info("=" * 60)
    
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
        logger.info("Bot shut down by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in standalone runner: {e}")
        sys.exit(1)
