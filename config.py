import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Token from @BotFather
TOKEN = os.getenv("BOT_TOKEN", "8622390945:AAHEmKQlnk0PIzrMl7bdMpKiHPNlF6m6yAI").strip()

# Admin ID (Your Telegram ID) - Used for admin commands
ADMIN_ID = int(os.getenv("ADMIN_ID", "5047634413"))

# Rewards Configuration
WELCOME_POINTS = 10
REFERRAL_POINTS = 5
DAILY_POINTS = 2
MIN_WITHDRAW = 500

# AI Configuration (Gemini)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyBANNn8byDuYUXpc6cIDdCKXCKuFITfcmk")
GEMINI_MODEL = "gemini-2.0-flash"

# Force Subscribe Configuration (Optional)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")  # e.g. "@mychannel"
