import sys
import asyncio
from PyQt5.QtCore import QThread, pyqtSignal
from utils.logger import logger
from bot.telegram_bot import MediaBot
from downloader.ytdlp_handler import YTDownloader

class BotThread(QThread):
    """Background thread to run the asynchronous Telegram bot."""
    status_signal = pyqtSignal(str)
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.bot_instance = None
        self.loop = None
        
    def run(self):
        """Thread entry point."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.bot_instance = MediaBot(self.config_manager)
        
        self.status_signal.emit("STARTING")
        self.loop.run_until_complete(self.bot_instance.start_polling())
        
        # Keep loop running until cancelled
        if self.bot_instance.is_running:
            self.status_signal.emit("RUNNING")
            try:
                self.loop.run_forever()
            except asyncio.CancelledError:
                pass
        else:
             self.status_signal.emit("ERROR")

    def stop(self):
        """Stops the thread safely."""
        if self.bot_instance and self.bot_instance.is_running:
            # Schedule the stop coroutine in the running loop
            asyncio.run_coroutine_threadsafe(self.bot_instance.stop(), self.loop)
            self.status_signal.emit("STOPPING")
            
            # Stop the event loop
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)
                
        self.wait()
        self.status_signal.emit("STOPPED")


class ManualDownloadThread(QThread):
    """Background thread to handle manual downloads from GUI."""
    progress_signal = pyqtSignal(int, str, str)  # percent, speed, eta
    finished_signal = pyqtSignal(bool, str)      # success, msg
    
    def __init__(self, url, format_type, resolution, config_manager):
        super().__init__()
        self.url = url
        self.format_type = format_type
        self.resolution = resolution
        self.config_manager = config_manager
        
    def run(self):
        try:
            downloader = YTDownloader(
                download_dir=self.config_manager.get("download_path", "downloads/"),
                ffmpeg_path=self.config_manager.get("ffmpeg_path")
            )
            
            def progress_hook(percent, speed, eta):
                self.progress_signal.emit(int(percent), speed, eta)
                
            res = downloader._download_sync(self.url, self.format_type, self.resolution, progress_cb=progress_hook)
                
            if res.get('success'):
                # Database recording
                from utils.database import add_download_record
                import os
                fmt = f"{self.format_type.upper()} {self.resolution or ''}".strip()
                add_download_record(os.path.basename(res['file_path']), self.url, fmt, res['size'])
                
                self.finished_signal.emit(True, f"Successfully downloaded: {res['title']}")
            else:
                self.finished_signal.emit(False, str(res.get('error', 'Unknown Error')))
                
        except Exception as e:
            self.finished_signal.emit(False, str(e))
