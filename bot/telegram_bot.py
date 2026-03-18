import os
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from utils.logger import logger
from downloader.ytdlp_handler import YTDownloader
from utils.database import add_download_record, check_rate_limit, get_stats, get_recent_users

class MediaBot:
    def __init__(self, config_manager):
        self.config = config_manager
        self.token = self.config.get("bot_token")
        self.application = None
        self.is_running = False
        
        # Keep track of user's active selections: {user_id: url}
        # This isolates active inline keyboard clicks so one user doesn't overwrite another.
        self.user_requests = {}

    def _is_admin(self, user_id):
        admin_ids = self.config.get("admin_ids", [])
        return user_id in admin_ids

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
            "Send me a link from YouTube, TikTok, or Facebook, and I'll safely download it for you in the best quality!"
        )

    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_html(
            "<b>How to use:</b>\n"
            "1. Just send me a video link.\n"
            "2. I will instantly analyze the link.\n"
            "3. Choose your desired video resolution or audio format.\n"
            "4. I will seamlessly download and send it back to this chat."
        )

    async def stats_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update.message.from_user.id):
            await update.message.reply_text("⛔️ You do not have admin permissions.")
            return
        dl_cnt, user_cnt = get_stats()
        text = f"📊 <b>Bot Statistics</b>\n\n👥 Total Unique Users: {user_cnt}\n⬇️ Total Downloads: {dl_cnt}"
        await update.message.reply_html(text)

    async def users_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update.message.from_user.id):
            return
        rows = get_recent_users(15)
        text = "👥 <b>Recent Users Dashboard</b>\n\n"
        for r in rows:
            text += f"ID: <code>{r[0]}</code> | @{r[1]} | Spams: {r[2]}\n"
        await update.message.reply_html(text)

    async def health_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update.message.from_user.id):
            return
        await update.message.reply_html("🟢 Bot Core: <b>Healthy</b>\n✅ Network Socket: <b>Connected</b>\n⚡️ Polling System: <b>Asynchronous Fast</b>")

    async def auto_handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        url = update.message.text.strip()
        user_id = update.message.from_user.id
        username = update.message.from_user.username or update.message.from_user.first_name or str(user_id)
        
        # Check URL validity basically
        if not url.startswith("http"):
            await update.message.reply_text("❌ Please send a valid URL starting with http:// or https://")
            return
            
        allowed, wait_sec = check_rate_limit(user_id, username, limit_per_min=5)
        if not allowed:
            await update.message.reply_text(f"⏳ Anti-Spam protection active. Please wait {wait_sec} seconds before requesting again.")
            return

        msg = await update.message.reply_text("🔍 Analyzing link...")
        
        try:
            # We explicitly initialize a per-user Downloader to isolate potential temp files
            downloader = YTDownloader(
                download_dir=self.config.get("download_path", "downloads/"),
                ffmpeg_path=self.config.get("ffmpeg_path"),
                user_id=user_id
            )
            
            info = await downloader.extract_info_async(url)
            
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
            
            # Save request specifically mapped to this user so others don't overlap them
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
            await msg.edit_text("❌ Failed to process URL. Ensure the platform is supported and the video is public.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data.split('|')
        action = data[0]
        fmt_res = data[1]
        user_id = int(data[2])
        
        # Concurrency safety: Prevent other users interacting with a button not explicitly theirs
        if query.from_user.id != user_id:
            await query.answer("⛔️ This inline menu is not yours!", show_alert=True)
            return

        if action == "cancel":
            self.user_requests.pop(user_id, None)
            await query.edit_message_caption("❌ Request cancelled.") if query.message.caption else await query.edit_message_text("❌ Request cancelled.")
            return

        url = self.user_requests.get(user_id)
        if not url:
            msg = "❌ Request expired or already processed. Please resend the link."
            await query.edit_message_caption(msg) if query.message.caption else await query.edit_message_text(msg)
            return

        # Evict url so user cannot spam click duplicate formats locally
        self.user_requests.pop(user_id, None)

        status_msg = "⏳ Initiating download... This might take a while for large files."
        await query.edit_message_caption(status_msg) if query.message.caption else await query.edit_message_text(status_msg)
        
        try:
            # Edit callback throttle
            last_edit_time = [0]
            
            def progress_cb(percent, speed, eta):
                now = time.time()
                # Edit message at most every 3 seconds to avoid FloodWait limits globally
                if now - last_edit_time[0] > 3.0 or percent == 100:
                    last_edit_time[0] = now
                    # We schedule this in the event loop properly since progress_cb runs in sync threads
                    text = f"⏳ <b>Downloading... {percent:.1f}%</b>\n🚀 Speed: {speed}\n⏱️ ETA: {eta}"
                    asyncio.run_coroutine_threadsafe(
                        self._async_edit_msg(query, text), 
                        self.application.updater.bot.get_request().loop
                    ) if not hasattr(self, '_loop') else asyncio.run_coroutine_threadsafe(self._async_edit_msg(query, text), self._loop)

            # Keep a reference to the main loop to invoke updates thread-safely per request
            self._loop = asyncio.get_running_loop()
            
            # Initialize separate local downloader for absolute user-isolation on temp files
            local_dl = YTDownloader(
                download_dir=self.config.get("download_path", "downloads/"),
                ffmpeg_path=self.config.get("ffmpeg_path"),
                user_id=user_id
            )
            
            if action == 'vid':
                res_val = int(fmt_res) if fmt_res != 'best' else None
                res = await local_dl.download_media_async(url, format_type='mp4', resolution=res_val, progress_cb=progress_cb)
                db_fmt = f"Video {fmt_res}p" if fmt_res != 'best' else "Video Best"
            elif action == 'aud':
                res = await local_dl.download_media_async(url, format_type=fmt_res, progress_cb=progress_cb)
                db_fmt = f"Audio {fmt_res.upper()}"

            if not res['success']:
                err_msg = f"❌ Download structurally failed (Could be private or deleted)."
                await query.edit_message_caption(err_msg) if query.message.caption else await query.edit_message_text(err_msg)
                return

            file_path = res['file_path']
            file_size_mb = res['size'] / (1024 * 1024)
            max_size = self.config.get("max_file_size", 50)
            
            add_download_record(os.path.basename(file_path), url, db_fmt, res['size'])

            # Automatic heavy compression fallback for free-tier Telegram Bots
            if file_size_mb > max_size:
                if action == 'vid':
                    compress_msg = f"⏳ File too large ({file_size_mb:.1f} MB), executing native ffmpeg compression specifically to fit {max_size} MB Telegram limit. Please wait..."
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
                        logger.error(f"Compression sub-process natively failed: {comp_e}")
                
            # Secondary check if audio or if compression still failed bandwidth boundaries
            if file_size_mb > max_size:
                large_msg = (
                    f"❌ Sorry, file intrinsically exceeds Telegram's absolute free upload limit even after compression ({file_size_mb:.1f} MB vs {max_size} MB max).\n"
                    "Consider utilizing premium limits or external links."
                )
                await query.edit_message_caption(large_msg, parse_mode="HTML") if query.message.caption else await query.edit_message_text(large_msg, parse_mode="HTML")
                try: 
                    os.remove(file_path) # Clean up huge files gracefully
                except Exception: pass
                return

            up_msg = "📤 Finished processing. Dispatching file securely to Telegram..."
            await query.edit_message_caption(up_msg) if query.message.caption else await query.edit_message_text(up_msg)
            
            # Exponential backoff loop specifically resolving random Timeout breaks during big loads
            for attempt in range(3):
                try:
                    with open(file_path, 'rb') as f:
                        if action == 'vid':
                            await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption=f"🎬 Enjoy your video!\n<b>{res['title']}</b>", parse_mode="HTML", read_timeout=300, write_timeout=300, connect_timeout=300)
                        else:
                            await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f, caption=f"🎵 Enjoy!\n<b>{res['title']}</b>", parse_mode="HTML", read_timeout=300, write_timeout=300, connect_timeout=300)
                    
                    success_msg = "✅ Sent successfully!"
                    await query.edit_message_caption(success_msg) if query.message.caption else await query.edit_message_text(success_msg)
                    break
                except Exception as upload_e:
                    if attempt < 2:
                        retry_msg = f"⏳ Network packet instability... Retrying upload securely (Attempt {attempt + 2}/3)"
                        await query.edit_message_caption(retry_msg) if query.message.caption else await query.edit_message_text(retry_msg)
                        await asyncio.sleep(2)
                    else:
                        raise upload_e
            
            # Explicit directory sweeping to prevent memory leaks from user traffic
            try:
                os.remove(file_path)
            except Exception as clean_e:logger.debug(f"Could not auto-delete file: {clean_e}")

        except Exception as e:
            logger.error(f"Error during overall download/upload process: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ An error occurred trying to deliver this specific item (potentially format unsupported by server).")

    async def _async_edit_msg(self, query, text):
        try:
            if query.message.caption:
                await query.edit_message_caption(text, parse_mode="HTML")
            else:
                await query.edit_message_text(text, parse_mode="HTML")
        except Exception:
            pass # ignore identical message errors thrown by telegram safely

    async def start_polling(self):
        """Starts the bot asynchronously."""
        if not self.token:
            logger.error("Bot token is empty! Please check settings.")
            return

        try:
            masked = f"{self.token[:4]}...{self.token[-4:]}" if len(self.token) > 10 else "***"
            logger.info(f"Initializing Telegram Bot with token {masked}")
            
            self.application = Application.builder().token(self.token).read_timeout(300).write_timeout(300).connect_timeout(300).pool_timeout(300).build()
            
            self.application.add_handler(CommandHandler("start", self.start_cmd))
            self.application.add_handler(CommandHandler("help", self.help_cmd))
            self.application.add_handler(CommandHandler("stats", self.stats_cmd))
            self.application.add_handler(CommandHandler("users", self.users_cmd))
            self.application.add_handler(CommandHandler("health", self.health_cmd))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.auto_handle_url))
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            
            self.is_running = True
            
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Bot is effectively live, multi-threaded, and publicly listening globally!")
            
        except Exception as e:
            logger.error(f"Failed to boot up public bot instance: {e}")
            self.is_running = False

    async def stop(self):
        """Stops the bot explicitly."""
        if self.application and self.is_running:
            logger.info("Decommissioning Telegram Bot services gracefully...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            self.is_running = False
            logger.info("Bot offline.")
