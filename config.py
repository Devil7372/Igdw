import os

API_ID = int(os.getenv("API_ID", "21185801"))
API_HASH = os.getenv("API_HASH", "4235ef431f138309cb9f56ae179a24ba")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7581945436:AAHhX7Msz_MnmPiZknn6ejbQbxZVzDrPQVw")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "7057341064").split(",")))
