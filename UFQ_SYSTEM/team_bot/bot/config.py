import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise ValueError("CRITICAL ERROR: BOT_TOKEN is missing or empty in .env file!")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
    if ADMIN_ID <= 0:
        raise ValueError("CRITICAL ERROR: ADMIN_ID is not set or invalid in .env file!")
except ValueError:
    raise ValueError("CRITICAL ERROR: ADMIN_ID must be a valid integer!")

DB_PATH = os.getenv("DB_PATH", "/home/ubuntu/UFQ_SYSTEM/shared/ufq_system.db")
