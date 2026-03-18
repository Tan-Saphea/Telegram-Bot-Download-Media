import os
import json

CONFIG_FILE = os.path.join("config", "config.json")

class SettingsManager:
    """Manages the application configuration settings."""
    def __init__(self):
        self.config = {
            "bot_token": "",
            "admin_ids": [],
            "download_path": "downloads/",
            "ffmpeg_path": "",
            "max_file_size": 50
        }
        self.load()

    def load(self):
        """Loads configuration from JSON file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            self.save()

    def save(self):
        """Saves current configuration to JSON file."""
        # Ensure config directory exists
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()
