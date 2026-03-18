import os
import yt_dlp
import asyncio
import re
from pathlib import Path
from utils.logger import logger

class DownloadProgressHook:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback

    def __call__(self, d):
        if d['status'] == 'downloading':
            try:
                # Calculate percentage safely
                percent_str = d.get('_percent_str', '0%').strip('\x1b[0;94m').strip('\x1b[0m').replace('%', '')
                percent_float = float(percent_str) if percent_str != 'Unknown' and percent_str != 'N/A' else 0.0
                speed = d.get('_speed_str', 'N/A').strip('\x1b[0;92m').strip('\x1b[0m')
                eta = d.get('_eta_str', 'N/A').strip('\x1b[0;93m').strip('\x1b[0m')
                if self.progress_callback:
                    self.progress_callback(percent_float, speed, eta)
            except Exception as e:
                logger.debug(f"Progress hook error: {e}")
        elif d['status'] == 'finished':
            if self.progress_callback:
                self.progress_callback(100.0, "Finished", "00:00")

class YTDownloader:
    """Download media from various platforms with security validations."""
    
    # Supported domains - whitelist approach for security
    ALLOWED_DOMAINS = {
        'youtube.com', 'youtu.be', 'youtube-nocookie.com',
        'tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com',
        'facebook.com', 'fb.watch',
        'instagram.com',
        'twitter.com', 'x.com',
        'dailymotion.com',
        'vimeo.com'
    }
    
    def __init__(self, download_dir, ffmpeg_path="", user_id="shared"):
        # Sanitize user_id to prevent path traversal
        user_id = str(user_id).split('/')[0].split('\\')[0][:20]  # Limit and prevent traversal
        self.download_dir = os.path.join(download_dir, user_id)
        
        # Ensure directory is under allowed base path
        base_path = os.path.abspath(download_dir)
        abs_download_dir = os.path.abspath(self.download_dir)
        if not abs_download_dir.startswith(base_path):
            logger.warning(f"Attempted path traversal: {abs_download_dir}")
            self.download_dir = os.path.join(download_dir, "safe")
        
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir, mode=0o755)
            
        self.ffmpeg_path = ffmpeg_path
        self.user_id = user_id

    @staticmethod
    def is_url_valid(url):
        """Validate and sanitize URL safely."""
        if not isinstance(url, str):
            return False
        
        url = url.strip()
        
        # Check basic URL format
        if not url.startswith(('http://', 'https://')):
            return False
        
        # URL length check (prevent ReDoS)
        if len(url) > 4096:
            return False
        
        # Check domain against whitelist
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace('www.', '')
            
            # Check if domain is allowed
            is_allowed = any(domain.endswith(allowed) for allowed in YTDownloader.ALLOWED_DOMAINS)
            
            if not is_allowed:
                logger.warning(f"Domain not in whitelist: {domain}")
                return False
            
            return True
        except Exception as e:
            logger.warning(f"URL validation error: {e}")
            return False

    def get_base_options(self):
        opts = {
            'outtmpl': os.path.join(self.download_dir, '%(title).150s [%(resolution)s].%(ext)s'),
            'restrictfilenames': True,  # Clean filenames (remove emojis/symbols)
            'windowsfilenames': True,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        # Validate and set ffmpeg path securely
        if self.ffmpeg_path:
            ffmpeg_path_abs = os.path.abspath(self.ffmpeg_path)
            # Check if ffmpeg path is valid (is a file or directory)
            if os.path.isdir(self.ffmpeg_path) and os.path.exists(os.path.join(self.ffmpeg_path, 'ffmpeg')):
                opts['ffmpeg_location'] = self.ffmpeg_path
            elif os.path.isfile(self.ffmpeg_path):
                opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)
        
        return opts

    async def extract_info_async(self, url):
        """Extract video information asynchronously."""
        if not self.is_url_valid(url):
            raise ValueError("Invalid or unsupported URL")
        return await asyncio.to_thread(self._extract_info_sync, url)

    def _extract_info_sync(self, url):
        """Extract video information synchronously."""
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
                    'title': str(info.get('title', 'Unknown Title'))[:200],  # Limit title length
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', None),
                    'resolutions': available
                }
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            raise

    async def download_media_async(self, url, format_type, resolution=None, progress_cb=None):
        """Dynamic download method supporting varying audio/video formats."""
        if not self.is_url_valid(url):
            raise ValueError("Invalid or unsupported URL")
        return await asyncio.to_thread(self._download_sync, url, format_type, resolution, progress_cb)

    def _download_sync(self, url, format_type, resolution=None, progress_cb=None):
        """Download media with security checks."""
        opts = self.get_base_options()
        hook = DownloadProgressHook(progress_callback=progress_cb)
        opts['progress_hooks'] = [hook]

        # Validate format_type
        if not isinstance(format_type, str) or format_type not in ['mp3', 'm4a', 'mp4']:
            logger.warning(f"Invalid format type: {format_type}")
            format_type = 'mp4'

        # Ensure ffmpeg is available
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
                try:
                    resolution = int(resolution)
                    if resolution < 144 or resolution > 4320:
                        resolution = None
                except (ValueError, TypeError):
                    resolution = None
                
                if resolution and has_ffmpeg:
                    opts['format'] = f'bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]/best[height<={resolution}][ext=mp4]/best'
                elif resolution:
                    opts['format'] = f'best[height<={resolution}][ext=mp4]/best'
                elif has_ffmpeg:
                    opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                else:
                    opts['format'] = 'best[ext=mp4]/best'
            else:
                if has_ffmpeg:
                    opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                else:
                    opts['format'] = 'best[ext=mp4]/best'
            
            if has_ffmpeg:
                opts['merge_output_format'] = 'mp4'

        try:
            logger.info(f"Downloading {format_type} {resolution or 'best'}: {url[:100]}")
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
                
                # Verify file is within allowed directory
                abs_file = os.path.abspath(actual_file)
                abs_download_dir = os.path.abspath(self.download_dir)
                if not abs_file.startswith(abs_download_dir):
                    logger.warning(f"File outside download directory: {abs_file}")
                    raise ValueError("Downloaded file is outside allowed directory")
                        
                size = os.path.getsize(actual_file) if os.path.exists(actual_file) else 0

                return {
                    'success': True,
                    'file_path': actual_file,
                    'title': info.get('title', 'Media')[:200],
                    'size': size
                }
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return {'success': False, 'error': str(e)}
