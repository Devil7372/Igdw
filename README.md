# Instagram Bot

A Telegram bot that downloads Instagram posts, reels, and IGTV videos.

## Features

- ✅ Download Instagram posts, reels, and IGTV
- 🔒 Force channel join before use
- 📊 Daily download limits per user
- 👨‍💼 Admin commands for broadcasting and statistics
- 🚀 Easy setup and deployment

## Setup

1. **Clone/Download the project**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Copy `.env.example` to `.env`
   - Fill in your credentials

4. **Run the bot:**
   ```bash
   python main.py
   ```

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | `1234567890:ABC...` |
| `ADMIN_USER_ID` | Your Telegram user ID | `123456789` |
| `FORCE_JOIN_CHANNEL` | Channel ID for forced join | `-1001234567890` |
| `YOUR_CHANNEL_LINK` | Public channel link | `https://t.me/channel` |
| `INSTAGRAM_USERNAME` | Instagram username | `your_username` |
| `INSTAGRAM_PASSWORD` | Instagram password | `your_password` |

### Optional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_DOWNLOADS_PER_DAY` | `10` | Daily download limit |
| `DOWNLOAD_TIMEOUT` | `30` | Download timeout (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Commands

### User Commands
- `/start` - Start the bot
- `/help` - Show help message
- `/stats` - Show usage statistics

### Admin Commands
- `/adminstats` - Show bot statistics
- `/broadcast` - Broadcast message to all users

## Support

For support, join our channel: [Your Channel Link]

## License

This project is for educational purposes only.
