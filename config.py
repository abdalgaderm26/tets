import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ======================================================================
# SECURITY: All sensitive values MUST be set via environment variables.
# Never hardcode tokens or API keys here — they would leak via GitHub.
# Set them in Railway's Environment Variables panel or a local .env file.
# ======================================================================

# Bot Token from @BotFather
TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN environment variable is not set!")

# Admin ID (Your Telegram ID) - Used for admin commands
# We default to a known value, but ALWAYS check environment first
ADMIN_ID = int(os.getenv("ADMIN_ID", "5047634413"))

# Rewards Configuration
WELCOME_POINTS = 10
REFERRAL_POINTS = 5
DAILY_POINTS = 2
MIN_WITHDRAW = 500

# AI Configuration (Gemini)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# Force Subscribe Configuration (Optional)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")  # e.g. "@mychannel"
