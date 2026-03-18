import os
import yt_dlp
import asyncio
from pathlib import Path
from utils.logger import logger

class DownloadProgressHook:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback

    def __call__(self, d):
        if d['status'] == 'downloading':
            try:
                # Calculate percentage
                percent_str = d.get('_percent_str', '0%').strip('\x1b[0;94m').strip('\x1b[0m').replace('%', '')
                percent_float = float(percent_str) if percent_str != 'Unknown' and percent_str != 'N/A' else 0.0
                speed = d.get('_speed_str', 'N/A').strip('\x1b[0;92m').strip('\x1b[0m')
                eta = d.get('_eta_str', 'N/A').strip('\x1b[0;93m').strip('\x1b[0m')
                if self.progress_callback:
                    self.progress_callback(percent_float, speed, eta)
            except Exception as e:
                pass
        elif d['status'] == 'finished':
            if self.progress_callback:
                self.progress_callback(100.0, "Finished", "00:00")

class YTDownloader:
    def __init__(self, download_dir, ffmpeg_path=""):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            
        self.ffmpeg_path = ffmpeg_path

    def get_base_options(self):
        opts = {
            'outtmpl': os.path.join(self.download_dir, '%(title).150s [%(resolution)s].%(ext)s'),
            'restrictfilenames': True,  # Clean filenames (remove emojis/symbols)
            'windowsfilenames': True,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        if self.ffmpeg_path and os.path.isdir(self.ffmpeg_path):
            opts['ffmpeg_location'] = self.ffmpeg_path
        return opts

    async def extract_info_async(self, url):
        return await asyncio.to_thread(self._extract_info_sync, url)

    def _extract_info_sync(self, url):
        opts = self.get_base_options()
        opts['extract_flat'] = False  # Need to check formats
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                heights = sorted(list(set(f.get('height') for f in formats if f.get('height'))), reverse=True)
                # We filter up to 1080p to fit common needs and keep sizes manageable
                available = [h for h in heights if h in [1080, 720, 480]]
                if not available and heights:
                    available = [heights[0]]
                
                return {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', None),
                    'resolutions': available
                }
        except Exception as e:
            logger.error(f"Extraction error payload: {e}")
            raise

    async def download_media_async(self, url, format_type, resolution=None, progress_cb=None):
        """Dynamic download method supporting varying audio/video formats"""
        return await asyncio.to_thread(self._download_sync, url, format_type, resolution, progress_cb)

    def _download_sync(self, url, format_type, resolution=None, progress_cb=None):
        opts = self.get_base_options()
        hook = DownloadProgressHook(progress_callback=progress_cb)
        opts['progress_hooks'] = [hook]

        # Ensure ffmpeg fallback
        has_ffmpeg = self.ffmpeg_path and os.path.exists(self.ffmpeg_path)

        if format_type in ['mp3', 'm4a']:
            opts['format'] = 'bestaudio/best'
            opts['outtmpl'] = os.path.join(self.download_dir, '%(title).150s.%(ext)s')
            if has_ffmpeg:
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_type,
                    'preferredquality': '192',
                }]
        else:
            if resolution:
                if has_ffmpeg:
                    opts['format'] = f'bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]/best[height<={resolution}][ext=mp4]/best'
                else:
                    opts['format'] = f'best[height<={resolution}][ext=mp4]/best'
            else:
                if has_ffmpeg:
                    opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                else:
                    opts['format'] = 'best[ext=mp4]/best'
            if has_ffmpeg:
                opts['merge_output_format'] = 'mp4'

        try:
            logger.info(f"Downloading {format_type} {resolution or ''}: {url}")
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                
                # Check actual output paths (clean extension swaps if postprocessed)
                base_name = os.path.splitext(file_path)[0]
                possible = [file_path, base_name + '.mp3', base_name + '.m4a', base_name + '.mp4', base_name + '.mkv', base_name + '.webm']
                actual_file = file_path
                for p in possible:
                    if os.path.exists(p):
                        actual_file = p
                        break
                        
                size = os.path.getsize(actual_file) if os.path.exists(actual_file) else 0

                return {
                    'success': True,
                    'file_path': actual_file,
                    'title': info.get('title', 'Media'),
                    'size': size
                }
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return {'success': False, 'error': str(e)}
