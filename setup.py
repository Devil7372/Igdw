#!/usr/bin/env python3
"""Instagram Bot Setup Script"""

import os
import sys
import subprocess

def install_requirements():
    print("📦 Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ Requirements installed successfully!")

def create_env_file():
    if not os.path.exists('.env'):
        print("📝 Creating .env file...")
        with open('.env', 'w') as f:
            f.write("""# Instagram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=123456789
FORCE_JOIN_CHANNEL=-1001234567890
YOUR_CHANNEL_LINK=https://t.me/your_channel_username
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
MAX_DOWNLOADS_PER_DAY=10
DOWNLOAD_TIMEOUT=30
LOG_LEVEL=INFO
""")
        print("✅ .env file created! Please edit it with your credentials.")
    else:
        print("⚠️  .env file already exists.")

def main():
    print("🚀 Instagram Bot Setup")
    print("=" * 50)

    try:
        install_requirements()
        create_env_file()

        print("\n🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Edit the .env file with your credentials")
        print("2. Run: python main.py")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
