import os
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from utils.logger import logger
from downloader.ytdlp_handler import YTDownloader
from utils.database import add_download_record, check_rate_limit

class MediaBot:
    def __init__(self, config_manager):
        self.config = config_manager
        self.token = self.config.get("bot_token")
        self.application = None
        self.downloader = YTDownloader(
            download_dir=self.config.get("download_path", "downloads/"),
            ffmpeg_path=self.config.get("ffmpeg_path")
        )
        self.is_running = False
        
        # Keep track of user's active selections: {user_id: url}
        self.user_requests = {}

    def format_duration(self, seconds):
        if not seconds:
            return "Unknown"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_html(
            "Welcome to <b>Media Downloader Bot</b>! 🎥🎵\n\n"
            "Send me a link from YouTube, TikTok, or Facebook, and I'll help you download it in the best quality."
        )

    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_html(
            "<b>How to use:</b>\n"
            "1. Just send me a video link.\n"
            "2. I will analyze the link.\n"
            "3. Choose your desired video resolution or audio format.\n"
            "4. I will download and send it directly to you!"
        )

    async def auto_handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        url = update.message.text.strip()
        user_id = update.message.from_user.id
        username = update.message.from_user.username or update.message.from_user.first_name or str(user_id)
        
        # Check URL validity basically
        if not url.startswith("http"):
            await update.message.reply_text("Please send a valid URL starting with http:// or https://")
            return
            
        allowed, wait_sec = check_rate_limit(user_id, username, limit_per_min=5)
        if not allowed:
            await update.message.reply_text(f"⏳ Rate limit exceeded. Please wait {wait_sec} seconds before requesting again.")
            return

        msg = await update.message.reply_text("🔍 Analyzing link...")
        
        try:
            self.downloader = YTDownloader(
                download_dir=self.config.get("download_path", "downloads/"),
                ffmpeg_path=self.config.get("ffmpeg_path")
            )
            
            info = await self.downloader.extract_info_async(url)
            
            title = info.get('title', 'Unknown Media')
            duration = self.format_duration(info.get('duration'))
            resolutions = info.get('resolutions', [])
            
            text = (
                f"🎬 <b>{title}</b>\n"
                f"⏱️ <b>Duration:</b> {duration}\n\n"
                f"👇 Choose download format:"
            )
            
            keyboard = []
            
            # Video qualities
            vid_row = []
            for res in resolutions:
                vid_row.append(InlineKeyboardButton(f"🎬 {res}p", callback_data=f"vid|{res}|{user_id}"))
            
            # Chunk video buttons to max 2 per row
            for i in range(0, len(vid_row), 2):
                keyboard.append(vid_row[i:i+2])
                
            # If no resolutions found, add default best video button
            if not resolutions:
                keyboard.append([InlineKeyboardButton("🎬 Best Video", callback_data=f"vid|best|{user_id}")])

            # Audio qualities
            keyboard.append([
                InlineKeyboardButton("🎵 MP3", callback_data=f"aud|mp3|{user_id}"),
                InlineKeyboardButton("🎵 M4A", callback_data=f"aud|m4a|{user_id}")
            ])
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|0|{user_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            self.user_requests[user_id] = url
            
            thumbnail = info.get('thumbnail')
            if thumbnail:
                try:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=thumbnail, caption=text, reply_markup=reply_markup, parse_mode="HTML")
                    await msg.delete()
                except Exception as e:
                    logger.warning(f"Could not send thumbnail UI: {e}")
                    await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Bot failed to process URL {url}: {e}")
            await msg.edit_text(f"❌ Failed to process URL. Ensure the platform is supported and the video is public.\n\nError: {str(e)[:100]}...")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data.split('|')
        action = data[0]
        fmt_res = data[1]
        user_id = int(data[2])
        
        if query.from_user.id != user_id:
            await query.answer("This is not your request!", show_alert=True)
            return

        if action == "cancel":
            self.user_requests.pop(user_id, None)
            await query.edit_message_caption("❌ Request cancelled.") if query.message.caption else await query.edit_message_text("❌ Request cancelled.")
            return

        url = self.user_requests.get(user_id)
        if not url:
            msg = "❌ Request expired or invalid. Please send the link again."
            await query.edit_message_caption(msg) if query.message.caption else await query.edit_message_text(msg)
            return

        self.user_requests.pop(user_id, None)

        status_msg = "⏳ Downloading... This might take a while."
        await query.edit_message_caption(status_msg) if query.message.caption else await query.edit_message_text(status_msg)
        
        try:
            # Edit callback throttle
            last_edit_time = [0]
            
            def progress_cb(percent, speed, eta):
                now = time.time()
                # Edit message at most every 3 seconds to avoid FloodWait limits
                if now - last_edit_time[0] > 3.0 or percent == 100:
                    last_edit_time[0] = now
                    # We have to schedule this in the event loop properly since progress_cb is mostly called from sync thread
                    text = f"⏳ <b>Downloading... {percent:.1f}%</b>\n🚀 Speed: {speed}\n⏱️ ETA: {eta}"
                    asyncio.run_coroutine_threadsafe(
                        self._async_edit_msg(query, text), 
                        self.application.updater.bot.get_request().loop  # hacky way to get the event loop
                    ) if not hasattr(self, '_loop') else asyncio.run_coroutine_threadsafe(self._async_edit_msg(query, text), self._loop)

            # Keep a reference to the main loop to invoke updates thread-safely
            self._loop = asyncio.get_running_loop()
            
            if action == 'vid':
                res_val = int(fmt_res) if fmt_res != 'best' else None
                res = await self.downloader.download_media_async(url, format_type='mp4', resolution=res_val, progress_cb=progress_cb)
                db_fmt = f"Video {fmt_res}p" if fmt_res != 'best' else "Video Best"
            elif action == 'aud':
                res = await self.downloader.download_media_async(url, format_type=fmt_res, progress_cb=progress_cb)
                db_fmt = f"Audio {fmt_res.upper()}"

            if not res['success']:
                err_msg = f"❌ Download failed: {res.get('error')}"
                await query.edit_message_caption(err_msg) if query.message.caption else await query.edit_message_text(err_msg)
                return

            file_path = res['file_path']
            file_size_mb = res['size'] / (1024 * 1024)
            max_size = self.config.get("max_file_size", 50)
            
            add_download_record(os.path.basename(file_path), url, db_fmt, res['size'])

            if file_size_mb > max_size:
                if action == 'vid':
                    compress_msg = f"⏳ File too large ({file_size_mb:.1f} MB), compressing to fit {max_size} MB limit..."
                    await query.edit_message_caption(compress_msg) if query.message.caption else await query.edit_message_text(compress_msg)
                    
                    compressed_file = file_path.rsplit('.', 1)[0] + '_compressed.mp4'
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            'ffmpeg', '-y', '-i', file_path, '-vf', 'scale=-2:480', '-vcodec', 'libx264', '-crf', '28', '-preset', 'fast', compressed_file,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await proc.wait()
                        
                        if os.path.exists(compressed_file):
                            try:
                                os.remove(file_path)
                            except Exception:
                                pass
                            file_path = compressed_file
                            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    except Exception as comp_e:
                        logger.error(f"Compression failed: {comp_e}")
                
            # Final check just in case compression wasn't enough or it is audio
            if file_size_mb > max_size:
                large_msg = (
                    f"❌ File is still too large for Telegram ({file_size_mb:.1f} MB).\n\n"
                    f"Telegram bot max limit is {max_size}MB.\nSaved natively as:\n<code>{os.path.basename(file_path)}</code>"
                )
                await query.edit_message_caption(large_msg, parse_mode="HTML") if query.message.caption else await query.edit_message_text(large_msg, parse_mode="HTML")
                return

            up_msg = "📤 Uploading file to Telegram..."
            await query.edit_message_caption(up_msg) if query.message.caption else await query.edit_message_text(up_msg)
            
            for attempt in range(3):
                try:
                    with open(file_path, 'rb') as f:
                        if action == 'vid':
                            await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption=f"Enjoy your video!\n<b>{res['title']}</b>", parse_mode="HTML", read_timeout=300, write_timeout=300, connect_timeout=300)
                        else:
                            await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f, caption=f"Enjoy!\n<b>{res['title']}</b>", parse_mode="HTML", read_timeout=300, write_timeout=300, connect_timeout=300)
                    
                    success_msg = "✅ Sent successfully!"
                    await query.edit_message_caption(success_msg) if query.message.caption else await query.edit_message_text(success_msg)
                    break
                except Exception as upload_e:
                    if attempt < 2:
                        retry_msg = f"⏳ Retrying upload... (Attempt {attempt + 2}/3)"
                        await query.edit_message_caption(retry_msg) if query.message.caption else await query.edit_message_text(retry_msg)
                        await asyncio.sleep(2)
                    else:
                        raise upload_e
            
            # Auto clean up to save space
            try:
                os.remove(file_path)
            except Exception as clean_e:
                logger.debug(f"Could not auto-delete file: {clean_e}")

        except Exception as e:
            logger.error(f"Error during download/upload process: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ An error occurred: {str(e)[:100]}")

    async def _async_edit_msg(self, query, text):
        try:
            if query.message.caption:
                await query.edit_message_caption(text, parse_mode="HTML")
            else:
                await query.edit_message_text(text, parse_mode="HTML")
        except Exception:
            pass # ignore identical message errors

    async def start_polling(self):
        """Starts the bot using polling."""
        if not self.token:
            logger.error("Bot token is empty! Please check settings.")
            return

        try:
            # Mask token for logging:
            masked = f"{self.token[:4]}...{self.token[-4:]}" if len(self.token) > 10 else "***"
            logger.info(f"Initializing Telegram Bot with token {masked}")
            
            self.application = Application.builder().token(self.token).read_timeout(300).write_timeout(300).connect_timeout(300).pool_timeout(300).build()
            
            self.application.add_handler(CommandHandler("start", self.start_cmd))
            self.application.add_handler(CommandHandler("help", self.help_cmd))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.auto_handle_url))
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            
            self.is_running = True
            
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Bot is running globally!")
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            self.is_running = False

    async def stop(self):
        """Stops the bot."""
        if self.application and self.is_running:
            logger.info("Stopping Telegram Bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            self.is_running = False
            logger.info("Bot stopped.")
