import os
import logging
from urllib.parse import urlparse
import instaloader
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
TELEGRAM_BOT_TOKEN = "7581945436:AAHhX7Msz_MnmPiZknn6ejbQbxZVzDrPQVw"  # Replace with your Telegram Bot Token
INSTAGRAM_USERNAME = "your_instagram_username" # Replace with your Instagram username
INSTAGRAM_PASSWORD = "your_instagram_password" # Replace with your Instagram password

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Instaloader Initialization ---
L = instaloader.Instaloader()

# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Hello! Send me a link to an Instagram post or Reel, and I will download it for you."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming messages and processes Instagram links."""
    message_text = update.message.text
    if "instagram.com" in message_text:
        await download_instagram_post(update, context, message_text)
    else:
        await update.message.reply_text("Please send a valid Instagram link.")

# --- Instagram Download Logic ---

async def download_instagram_post(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Downloads the Instagram post or Reel and sends it to the user."""
    await update.message.reply_text("Processing your request...")

    try:
        # Login to Instagram
        L.load_session_from_file(INSTAGRAM_USERNAME)
    except FileNotFoundError:
        try:
            L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            L.save_session_to_file(INSTAGRAM_USERNAME)
        except Exception as e:
            logger.error(f"Instagram login failed: {e}")
            await update.message.reply_text("Could not log in to Instagram. Please check the credentials.")
            return

    try:
        # Extract the shortcode from the URL
        parsed_url = urlparse(url)
        shortcode = parsed_url.path.split('/')[-2]

        # Download the post
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Handle different post types
        if post.is_video:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=open(L.download_post(post, target=shortcode).video_url, 'rb'),
                caption=post.caption
            )
        else:
            media_group = []
            for node in post.get_sidecar_nodes():
                if node.is_video:
                    media_group.append(InputMediaVideo(media=open(L.download_post(post, target=shortcode).video_url, 'rb')))
                else:
                    media_group.append(InputMediaPhoto(media=open(L.download_post(post, target=shortcode).url, 'rb')))
            
            if media_group:
                 await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group, caption=post.caption)
            else: # For single image posts
                 await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(L.download_post(post, target=shortcode).url, 'rb'), caption=post.caption)

        # Clean up downloaded files
        for f in os.listdir(shortcode):
            os.remove(os.path.join(shortcode, f))
        os.rmdir(shortcode)

    except Exception as e:
        logger.error(f"Error downloading post: {e}")
        await update.message.reply_text("Sorry, I couldn't download the post. Please make sure the link is correct and the post is public.")

# --- Main Bot Execution ---

def main() -> None:
    """Start the bot."""
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # on non command i.e message - handle the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
