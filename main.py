import os
import logging
from urllib.parse import urlparse
import instaloader
from telegram import Update, InputMediaPhoto, InputMediaVideo, ForceReply
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.error import BadRequest
import json
import re
import shutil
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
FORCE_JOIN_CHANNEL = int(os.getenv("FORCE_JOIN_CHANNEL", "0"))
YOUR_CHANNEL_LINK = os.getenv("YOUR_CHANNEL_LINK")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
BOT_WELCOME_MESSAGE = os.getenv("BOT_WELCOME_MESSAGE", "🌟 Hello! I can download Instagram Reels and Posts for you.")
MAX_DOWNLOADS_PER_DAY = int(os.getenv("MAX_DOWNLOADS_PER_DAY", "10"))
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "30"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# File paths
USER_DATA_FILE = "bot_users.json"
DOWNLOAD_LIMITS_FILE = "download_limits.json"

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL.upper()),
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Configuration Validation ---
def validate_config():
    """Validates that all required environment variables are set."""
    required_vars = {
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "INSTAGRAM_USERNAME": INSTAGRAM_USERNAME,
        "INSTAGRAM_PASSWORD": INSTAGRAM_PASSWORD,
        "FORCE_JOIN_CHANNEL": FORCE_JOIN_CHANNEL,
        "YOUR_CHANNEL_LINK": YOUR_CHANNEL_LINK,
        "ADMIN_USER_ID": ADMIN_USER_ID,
    }
    
    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value or (isinstance(var_value, int) and var_value == 0):
            missing_vars.append(var_name)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file and ensure all variables are set correctly.")
        return False
    
    return True

# --- Instaloader Initialization ---
L = instaloader.Instaloader(
    download_pictures=True,
    download_videos=True,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
)

# --- User Data Management ---
def load_users():
    """Loads user IDs from the JSON file."""
    if not os.path.exists(USER_DATA_FILE):
        return set()
    try:
        with open(USER_DATA_FILE, "r") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid user data file, starting fresh")
        return set()

def save_users(users):
    """Saves user IDs to the JSON file."""
    try:
        with open(USER_DATA_FILE, "w") as f:
            json.dump(list(users), f)
    except Exception as e:
        logger.error(f"Failed to save users: {e}")

def load_download_limits():
    """Loads download limits from the JSON file."""
    if not os.path.exists(DOWNLOAD_LIMITS_FILE):
        return {}
    try:
        with open(DOWNLOAD_LIMITS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid download limits file, starting fresh")
        return {}

def save_download_limits(limits):
    """Saves download limits to the JSON file."""
    try:
        with open(DOWNLOAD_LIMITS_FILE, "w") as f:
            json.dump(limits, f)
    except Exception as e:
        logger.error(f"Failed to save download limits: {e}")

def check_download_limit(user_id):
    """Checks if user has exceeded daily download limit."""
    limits = load_download_limits()
    user_id_str = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user_id_str not in limits:
        limits[user_id_str] = {"date": today, "count": 0}
    
    user_limit = limits[user_id_str]
    if user_limit["date"] != today:
        user_limit["date"] = today
        user_limit["count"] = 0
    
    if user_limit["count"] >= MAX_DOWNLOADS_PER_DAY:
        return False
    
    user_limit["count"] += 1
    save_download_limits(limits)
    return True

user_ids = load_users()

# --- Utility Functions ---
def is_valid_instagram_url(url):
    """Validates Instagram URL format."""
    instagram_patterns = [
        r'https?://(?:www\.)?instagram\.com/p/([A-Za-z0-9_-]+)',
        r'https?://(?:www\.)?instagram\.com/reel/([A-Za-z0-9_-]+)',
        r'https?://(?:www\.)?instagram\.com/tv/([A-Za-z0-9_-]+)',
    ]
    return any(re.match(pattern, url) for pattern in instagram_patterns)

def extract_shortcode(url):
    """Extracts shortcode from Instagram URL."""
    patterns = [
        r'instagram\.com/p/([A-Za-z0-9_-]+)',
        r'instagram\.com/reel/([A-Za-z0-9_-]+)',
        r'instagram\.com/tv/([A-Za-z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def cleanup_directory(directory):
    """Safely removes directory and its contents."""
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
    except Exception as e:
        logger.error(f"Failed to cleanup directory {directory}: {e}")

# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message and logs new users."""
    user = update.effective_user
    if user.id not in user_ids:
        user_ids.add(user.id)
        save_users(user_ids)
        logger.info(f"New user started the bot: {user.first_name} (ID: {user.id})")

    await update.message.reply_text(
        f"{BOT_WELCOME_MESSAGE}\n\n"
        f"📢 But first, you must join our channel: {YOUR_CHANNEL_LINK}\n\n"
        f"After joining, send me the Instagram link and I'll download it for you! 📥\n\n"
        f"📊 Daily limit: {MAX_DOWNLOADS_PER_DAY} downloads per user\n\n"
        "🔗 Supported links:\n"
        "• instagram.com/p/... (Posts)\n"
        "• instagram.com/reel/... (Reels)\n"
        "• instagram.com/tv/... (IGTV)"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows help information."""
    help_text = (
        "🤖 **Bot Commands:**\n\n"
        "• Send any Instagram link to download\n"
        "• /start - Start the bot\n"
        "• /help - Show this help message\n"
        "• /stats - Show your usage stats\n\n"
        "🔗 **Supported Links:**\n"
        "• Instagram Posts (instagram.com/p/...)\n"
        "• Instagram Reels (instagram.com/reel/...)\n"
        "• Instagram IGTV (instagram.com/tv/...)\n\n"
        "⚠️ **Important:**\n"
        f"• You must join our channel: {YOUR_CHANNEL_LINK}\n"
        f"• Daily download limit: {MAX_DOWNLOADS_PER_DAY} per user\n"
        "• Only public posts can be downloaded\n"
        "• Bot works 24/7 automatically"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows user statistics."""
    user_id = update.effective_user.id
    limits = load_download_limits()
    user_id_str = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user_id_str in limits and limits[user_id_str]["date"] == today:
        downloads_today = limits[user_id_str]["count"]
    else:
        downloads_today = 0
    
    remaining = MAX_DOWNLOADS_PER_DAY - downloads_today
    
    stats_text = (
        f"📊 **Your Statistics:**\n\n"
        f"📥 Downloads today: {downloads_today}/{MAX_DOWNLOADS_PER_DAY}\n"
        f"⏳ Remaining: {remaining}\n"
        f"🔄 Resets: Daily at midnight\n\n"
        f"📢 Channel: {YOUR_CHANNEL_LINK}"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def force_join_checker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Checks if a user is a member of the required channel."""
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=FORCE_JOIN_CHANNEL, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            await update.message.reply_text(
                f"❌ You must join our channel to use this bot.\n\n"
                f"📢 Please join here: {YOUR_CHANNEL_LINK}\n\n"
                "After joining, send the Instagram link again! 🔄"
            )
            return False
    except BadRequest as e:
        if "user not found" in str(e).lower():
            await update.message.reply_text(
                f"❌ You must join our channel to use this bot.\n\n"
                f"📢 Please join here: {YOUR_CHANNEL_LINK}"
            )
        else:
            logger.error(f"Error checking channel membership: {e}")
            await update.message.reply_text("⚠️ An error occurred. Please try again later.")
        return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming messages and processes Instagram links."""
    if not await force_join_checker(update, context):
        return
    
    # Check download limit
    if not check_download_limit(update.effective_user.id):
        await update.message.reply_text(
            f"❌ You've reached your daily download limit of {MAX_DOWNLOADS_PER_DAY}.\n\n"
            "⏰ Your limit will reset at midnight.\n"
            f"📢 Join our channel for updates: {YOUR_CHANNEL_LINK}"
        )
        return

    message_text = update.message.text
    if is_valid_instagram_url(message_text):
        await download_instagram_post(update, context, message_text)
    else:
        await update.message.reply_text(
            "❌ Please send a valid Instagram link.\n\n"
            "✅ **Supported formats:**\n"
            "• instagram.com/p/... (Posts)\n"
            "• instagram.com/reel/... (Reels)\n"
            "• instagram.com/tv/... (IGTV)\n\n"
            "💡 **Example:**\n"
            "`https://www.instagram.com/p/ABC123/`",
            parse_mode='Markdown'
        )

# --- Instagram Download Logic ---

async def download_instagram_post(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Downloads the Instagram post and sends it to the user with a custom caption."""
    processing_message = await update.message.reply_text("🔄 Processing your request...")
    
    shortcode = extract_shortcode(url)
    if not shortcode:
        await processing_message.edit_text("❌ Invalid Instagram URL format.")
        return

    download_dir = f"downloads/{shortcode}_{int(time.time())}"
    
    try:
        # Create download directory
        os.makedirs(download_dir, exist_ok=True)
        
        # Download the post
        await processing_message.edit_text("📥 Downloading from Instagram...")
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=download_dir)
        
        # Custom caption
        caption = (
            f"📥 Downloaded by your bot!\n\n"
            f"📢 Join our channel: {YOUR_CHANNEL_LINK}\n"
            f"🤖 Made with ❤️"
        )
        
        # Find downloaded files
        downloaded_files = []
        for file_path in Path(download_dir).glob("*"):
            if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.mp4']:
                downloaded_files.append(file_path)
        
        downloaded_files.sort()
        
        if not downloaded_files:
            await processing_message.edit_text("❌ No media files found in the post.")
            return
        
        await processing_message.edit_text("📤 Uploading media...")
        
        # Handle single file
        if len(downloaded_files) == 1:
            file_path = downloaded_files[0]
            try:
                with open(file_path, 'rb') as media_file:
                    if file_path.suffix.lower() == '.mp4':
                        await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=media_file,
                            caption=caption,
                            supports_streaming=True
                        )
                    else:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=media_file,
                            caption=caption
                        )
            except Exception as e:
                logger.error(f"Error sending single media: {e}")
                await processing_message.edit_text("❌ Failed to send media file.")
                return
        
        # Handle multiple files (carousel)
        else:
            media_group = []
            files_to_close = []
            
            try:
                for i, file_path in enumerate(downloaded_files[:10]):  # Telegram limit
                    file_obj = open(file_path, 'rb')
                    files_to_close.append(file_obj)
                    
                    media_caption = caption if i == 0 else ''
                    
                    if file_path.suffix.lower() == '.mp4':
                        media_group.append(InputMediaVideo(media=file_obj, caption=media_caption))
                    else:
                        media_group.append(InputMediaPhoto(media=file_obj, caption=media_caption))
                
                if media_group:
                    await context.bot.send_media_group(
                        chat_id=update.effective_chat.id,
                        media=media_group
                    )
                    
            except Exception as e:
                logger.error(f"Error sending media group: {e}")
                await processing_message.edit_text("❌ Failed to send media files.")
            finally:
                # Close all opened files
                for file_obj in files_to_close:
                    try:
                        file_obj.close()
                    except:
                        pass
        
        await processing_message.delete()
        
        # Send success message
        await update.message.reply_text(
            "✅ **Download completed successfully!**\n\n"
            f"📢 Don't forget to share our channel: {YOUR_CHANNEL_LINK}",
            parse_mode='Markdown'
        )
        
    except instaloader.exceptions.InstaloaderException as e:
        logger.error(f"Instaloader error: {e}")
        await processing_message.edit_text(
            "❌ **Failed to download the post.**\n\n"
            "This could be because:\n"
            "• The post is private 🔒\n"
            "• The post was deleted 🗑️\n"
            "• Instagram is blocking requests 🚫\n"
            "• Invalid link format ❌\n\n"
            "Please try again or use a different link."
        )
    except Exception as e:
        logger.error(f"Unexpected error downloading post: {e}")
        await processing_message.edit_text(
            "❌ **An unexpected error occurred.**\n\n"
            "Please try again later or contact support."
        )
    finally:
        # Clean up downloaded files
        cleanup_directory(download_dir)

# --- Admin Commands ---

BROADCAST_MESSAGE = range(1)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to check bot stats."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized access.")
        return
    
    limits = load_download_limits()
    today = datetime.now().strftime("%Y-%m-%d")
    today_downloads = sum(1 for user_data in limits.values() if user_data.get("date") == today)
    
    stats_text = (
        f"📊 **Bot Statistics:**\n\n"
        f"👥 Total users: {len(user_ids)}\n"
        f"📥 Downloads today: {today_downloads}\n"
        f"🤖 Bot status: Active\n"
        f"⚙️ Daily limit per user: {MAX_DOWNLOADS_PER_DAY}\n\n"
        f"📢 Channel: {YOUR_CHANNEL_LINK}"
    )
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin command to start the broadcast process."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized access.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📢 **Broadcast Mode**\n\n"
        "Please send the message you want to broadcast to all users.\n\n"
        "Use /cancel to abort.",
        reply_markup=ForceReply(),
        parse_mode='Markdown'
    )
    return BROADCAST_MESSAGE

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends the broadcast message to all users."""
    message = update.message.text
    await update.message.reply_text("🚀 Broadcast started... This may take a while.")
    
    success_count = 0
    fail_count = 0
    
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success_count += 1
            # Add small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
            fail_count += 1
    
    await update.message.reply_text(
        f"✅ **Broadcast completed!**\n\n"
        f"📤 Successfully sent: {success_count}\n"
        f"❌ Failed to send: {fail_count}",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the broadcast conversation."""
    await update.message.reply_text("❌ Broadcast cancelled.")
    return ConversationHandler.END

# --- Main Bot Execution ---

def main() -> None:
    """Start the bot."""
    # Validate configuration first
    if not validate_config():
        logger.error("Configuration validation failed. Bot cannot start.")
        return
    
    logger.info("✅ Configuration validated successfully")
    
    # Login to Instagram
    try:
        L.load_session_from_file(INSTAGRAM_USERNAME)
        logger.info(f"Loaded Instagram session for {INSTAGRAM_USERNAME}")
    except FileNotFoundError:
        try:
            logger.info("Logging into Instagram...")
            L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            L.save_session_to_file(INSTAGRAM_USERNAME)
            logger.info(f"Logged into Instagram as {INSTAGRAM_USERNAME} and saved session.")
        except Exception as e:
            logger.error(f"Instagram login failed: {e}")
            logger.error("Bot will continue but Instagram downloads may fail.")

    # Create downloads directory
    os.makedirs("downloads", exist_ok=True)

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation handler for broadcasting
    broadcast_handler = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)],
        },
        fallbacks=[CommandHandler("cancel", broadcast_cancel)],
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", user_stats))
    application.add_handler(CommandHandler("adminstats", admin_stats))
    application.add_handler(broadcast_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    logger.info("🚀 Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
