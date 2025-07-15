import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_IDS

app = Client("insta_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

users = set()
banned_users = set()

# --- Utils ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_instagram_data(insta_url):
    api_url = f"https://api.bhawanigarg.com/social/instagram/?url={insta_url}"
    try:
        res = requests.get(api_url)
        if res.status_code == 200:
            return res.json().get("links", [])
        else:
            return None
    except Exception:
        return None

# --- Start ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    users.add(message.from_user.id)
    await message.reply("👋 Send me any Instagram post URL and I'll fetch it for you!")

# --- Instagram Downloader ---
@app.on_message(filters.text & ~filters.command(["start", "broadcast", "ban", "unban"]))
async def downloader(client, message: Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        return await message.reply("🚫 You are banned from using this bot.")

    text = message.text.strip()
    if "instagram.com" in text:
        await message.reply("⏳ Downloading...")
        links = get_instagram_data(text)
        if links:
            for link in links:
                await message.reply_video(link) if ".mp4" in link else await message.reply_photo(link)
        else:
            await message.reply("⚠️ Failed to download media.")
    else:
        await message.reply("❌ Invalid link. Please send an Instagram post URL.")

# --- Broadcast (Admin only) ---
@app.on_message(filters.command("broadcast") & filters.user(ADMIN_IDS))
async def broadcast(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /broadcast Your message here")
    text = message.text.split(" ", 1)[1]
    success, fail = 0, 0
    for uid in users:
        try:
            await client.send_message(uid, text)
            success += 1
        except:
            fail += 1
    await message.reply(f"✅ Broadcast sent.\nSuccess: {success}, Failed: {fail}")

# --- Ban / Unban ---
@app.on_message(filters.command("ban") & filters.user(ADMIN_IDS))
async def ban_user(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /ban user_id")
    user_id = int(message.command[1])
    banned_users.add(user_id)
    await message.reply(f"✅ Banned user {user_id}")

@app.on_message(filters.command("unban") & filters.user(ADMIN_IDS))
async def unban_user(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /unban user_id")
    user_id = int(message.command[1])
    banned_users.discard(user_id)
    await message.reply(f"✅ Unbanned user {user_id}")

app.run()
