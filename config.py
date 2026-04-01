import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Token from @BotFather
TOKEN = os.getenv("BOT_TOKEN", "8622390945:AAHEmKQlnk0PIzrMl7bdMpKiHPNlF6m6yAI")

# Admin ID (Your Telegram ID) - Used for admin commands
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Replace with your Telegram ID if not in .env

# Rewards Configuration
WELCOME_POINTS = 10
REFERRAL_POINTS = 5
DAILY_POINTS = 2

# Force Subscribe Configuration (Optional)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")  # e.g. "@mychannel"
