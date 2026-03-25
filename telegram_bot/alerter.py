# telegram_bot/alerter.py
import telegram
import sys
import os

# Append project root to path so it can find config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

class TelegramAlerter:
    def __init__(self):
        """Initializes the Telegram Bot using credentials from config."""
        self.token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
        self.chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')
        
        if self.token:
            self.bot = telegram.Bot(token=self.token)
        else:
            self.bot = None
            print("⚠️ WARNING: Telegram Bot Token not found in config. Alerts will be muted.")

    async def send_alert(self, message: str):
        """Sends an asynchronous message to your Telegram app."""
        if not self.bot or not self.chat_id:
            return # Fail silently if keys aren't configured yet

        try:
            await self.bot.send_message(
                chat_id=self.chat_id, 
                text=message, 
                parse_mode='Markdown' # Allows us to use bold text in our alerts
            )
        except Exception as e:
            print(f"❌ [Telegram Error] Failed to send alert: {e}")