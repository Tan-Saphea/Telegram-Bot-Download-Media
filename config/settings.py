import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

CONFIG_FILE = os.path.join("config", "config.json")

class SettingsManager:
    """Manages the application configuration settings with environment variable support."""
    def __init__(self):
        self.config = {
            "bot_token": "",
            "admin_ids": [],
            "download_path": "downloads/",
            "ffmpeg_path": "",
            "max_file_size": 50,
            "database_path": "history.db",
            "log_dir": "logs/",
            "rate_limit_per_minute": 5,
            "enable_ssl_verify": True
        }
        self.load()

    def load(self):
        """Loads configuration from environment variables first, then JSON file."""
        # First, load from environment variables (takes precedence)
        self._load_from_env()
        
        # Then, load from JSON file (overrides defaults but not env vars)
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Only apply JSON config for keys that aren't set via environment
                    for key, value in data.items():
                        if not os.getenv(key.upper()):
                            self.config[key] = value
            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            self.save()

    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Bot token (CRITICAL - must be set)
        token = os.getenv("BOT_TOKEN")
        if token:
            self.config["bot_token"] = token
        
        # Paths
        if os.getenv("DOWNLOAD_PATH"):
            self.config["download_path"] = os.getenv("DOWNLOAD_PATH")
        if os.getenv("FFMPEG_PATH"):
            self.config["ffmpeg_path"] = os.getenv("FFMPEG_PATH")
        if os.getenv("DATABASE_PATH"):
            self.config["database_path"] = os.getenv("DATABASE_PATH")
        if os.getenv("LOG_DIR"):
            self.config["log_dir"] = os.getenv("LOG_DIR")
        
        # Size limits
        if os.getenv("MAX_FILE_SIZE_MB"):
            try:
                self.config["max_file_size"] = float(os.getenv("MAX_FILE_SIZE_MB"))
            except ValueError:
                pass
        
        # Admin IDs
        if os.getenv("ADMIN_IDS"):
            try:
                admin_str = os.getenv("ADMIN_IDS")
                self.config["admin_ids"] = [int(x.strip()) for x in admin_str.split(",") if x.strip()]
            except ValueError:
                pass
        
        # Rate limiting
        if os.getenv("RATE_LIMIT_PER_MINUTE"):
            try:
                self.config["rate_limit_per_minute"] = int(os.getenv("RATE_LIMIT_PER_MINUTE"))
            except ValueError:
                pass
        
        # SSL verification
        if os.getenv("ENABLE_SSL_VERIFY"):
            ssl_verify = os.getenv("ENABLE_SSL_VERIFY", "").lower()
            self.config["enable_ssl_verify"] = ssl_verify in ("true", "1", "yes")

    def save(self):
        """Saves current configuration to JSON file."""
        # Ensure config directory exists
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        try:
            # Never save the bot token to file if it came from environment
            config_to_save = dict(self.config)
            if os.getenv("BOT_TOKEN"):
                config_to_save["bot_token"] = ""  # Don't save env-based token to file
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()
    
    def validate(self):
        """Validates critical configuration settings."""
        errors = []
        
        if not self.config.get("bot_token") or self.config["bot_token"] == "YOUR_TOKEN_HERE":
            errors.append("BOT_TOKEN not configured. Set it via environment variable or config/config.json")
        
        if not self.config.get("download_path"):
            errors.append("DOWNLOAD_PATH not configured")
        
        return errors
