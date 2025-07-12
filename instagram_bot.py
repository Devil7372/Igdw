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

# --- Configuration ---
TELEGRAM_BOT_TOKEN = "7581945436:AAHhX7Msz_MnmPiZknn6ejbQbxZVzDrPQVw"  # Replace with your bot token
INSTAGRAM_USERNAME = "devilarthub"  # Replace with your Instagram username
INSTAGRAM_PASSWORD = "DEVIL90₹"  # Replace with your Instagram password
FORCE_JOIN_CHANNEL = -1002403161861  # Replace with your channel's ID (must start with -100)
YOUR_CHANNEL_LINK = "https://t.me/DevilArtHub" # Replace with your channel's link
ADMIN_USER_ID = 7057341064  # Replace with your Telegram User ID
USER_DATA_FILE = "bot_users.json"

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Instaloader Initialization ---
L = instaloader.Instaloader()

# --- User Data Management ---
def load_users():
    """Loads user IDs from the JSON file."""
    if not os.path.exists(USER_DATA_FILE):
        return set()
    with open(USER_DATA_FILE, "r") as f:
        return set(json.load(f))

def save_users(users):
    """Saves user IDs to the JSON file."""
    with open(USER_DATA_FILE, "w") as f:
        json.dump(list(users), f)

user_ids = load_users()

# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message and logs new users."""
    user = update.effective_user
    if user.id not in user_ids:
        user_ids.add(user.id)
        save_users(user_ids)
        logger.info(f"New user started the bot: {user.first_name} (ID: {user.id})")

    await update.message.reply_text(
        "Hello! I can download Instagram Reels and Posts for you.\n"
        f"But first, you must join our channel: {YOUR_CHANNEL_LINK}\n\n"
        "After joining, send me the Instagram link."
    )

async def force_join_checker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Checks if a user is a member of the required channel."""
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=FORCE_JOIN_CHANNEL, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            await update.message.reply_text(
                f"You must join our channel to use this bot.\n"
                f"Please join here: {YOUR_CHANNEL_LINK}"
            )
            return False
    except BadRequest as e:
        if "user not found" in str(e).lower():
             await update.message.reply_text(
                f"You must join our channel to use this bot.\n"
                f"Please join here: {YOUR_CHANNEL_LINK}"
            )
        else:
            logger.error(f"Error checking channel membership: {e}")
            await update.message.reply_text("An error occurred. Please try again later.")
        return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming messages and processes Instagram links."""
    if not await force_join_checker(update, context):
        return

    message_text = update.message.text
    if "instagram.com" in message_text:
        await download_instagram_post(update, context, message_text)
    else:
        await update.message.reply_text("Please send a valid Instagram link.")

# --- Instagram Download Logic ---

async def download_instagram_post(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Downloads the Instagram post and sends it to the user with a custom caption."""
    await update.message.reply_text("Processing your request...")

    try:
        # Extract the shortcode from the URL
        parsed_url = urlparse(url)
        shortcode = parsed_url.path.split('/')[-2]

        # Download the post
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        caption = f"Downloaded by your bot!\n\nJoin us: {YOUR_CHANNEL_LINK}"

        # Handle different post types
        if post.is_video:
            video_path = L.download_post(post, target=shortcode).video_url
            with open(video_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    caption=caption
                )
        else:
            media_group = []
            nodes = post.get_sidecar_nodes()
            # Download all media first
            L.download_post(post, target=shortcode)
            
            # Find downloaded files
            downloaded_files = os.listdir(shortcode)
            media_files = sorted([os.path.join(shortcode, f) for f in downloaded_files if f.endswith(('.jpg', '.jpeg', '.png', '.mp4'))])

            for i, media_path in enumerate(media_files):
                media_caption = caption if i == 0 else ''
                if media_path.endswith('.mp4'):
                    media_group.append(InputMediaVideo(media=open(media_path, 'rb'), caption=media_caption))
                else:
                    media_group.append(InputMediaPhoto(media=open(media_path, 'rb'), caption=media_caption))

            if not media_group: # For single image posts
                image_path = [os.path.join(shortcode, f) for f in downloaded_files if f.endswith(('.jpg', '.jpeg', '.png'))][0]
                with open(image_path, 'rb') as photo_file:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_file, caption=caption)
            else:
                 await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group)

        # Clean up downloaded files
        for f in os.listdir(shortcode):
            os.remove(os.path.join(shortcode, f))
        os.rmdir(shortcode)

    except Exception as e:
        logger.error(f"Error downloading post: {e}")
        await update.message.reply_text("Sorry, I couldn't download the post. Make sure the link is correct and the post is public.")

# --- Admin Commands ---

BROADCAST_MESSAGE = range(1)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to check bot stats."""
    if update.effective_user.id != ADMIN_USER_ID:
        return
    await update.message.reply_text(f"Total users: {len(user_ids)}")

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin command to start the broadcast process."""
    if update.effective_user.id != ADMIN_USER_ID:
        return ConversationHandler.END
    await update.message.reply_text("Please send the message you want to broadcast to all users.", reply_markup=ForceReply())
    return BROADCAST_MESSAGE

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends the broadcast message to all users."""
    message = update.message.text
    await update.message.reply_text("Broadcast started... This may take a while.")
    
    success_count = 0
    fail_count = 0
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
            fail_count += 1
    
    await update.message.reply_text(f"Broadcast finished.\nSent: {success_count}\nFailed: {fail_count}")
    return ConversationHandler.END

async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the broadcast conversation."""
    await update.message.reply_text("Broadcast cancelled.")
    return ConversationHandler.END

# --- Main Bot Execution ---

def main() -> None:
    """Start the bot."""
    # Login to Instagram
    try:
        L.load_session_from_file(INSTAGRAM_USERNAME)
    except FileNotFoundError:
        try:
            L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            L.save_session_to_file(INSTAGRAM_USERNAME)
            logger.info(f"Logged into Instagram as {INSTAGRAM_USERNAME} and saved session.")
        except Exception as e:
            logger.error(f"Instagram login failed: {e}")
            return

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
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(broadcast_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
