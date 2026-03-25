# telegram_bot/bot.py
import sys
import os
import asyncio
import logging
from telegram import Update, Bot
from telegram.error import NetworkError
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

# Suppress the massive underlying httpx logging spam
logging.getLogger("httpx").setLevel(logging.WARNING)

class TelegramAlerter:
    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token) if self.token else None
        
        if self.token:
            self.app = ApplicationBuilder().token(self.token).build()
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("status", self.status_command))
            # Register the graceful error handler
            self.app.add_error_handler(self.error_handler)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Silently handles network disconnects without crashing the terminal."""
        if isinstance(context.error, NetworkError):
            # It's just a Wi-Fi drop or DNS failure, ignore it. The bot will auto-reconnect.
            pass
        else:
            print(f"[Telegram Bot] Non-network error occurred: {context.error}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🟢 Apex Trading Terminal Online. Monitoring 15m signals.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📊 System Status: ALL ENGINES RUNNING")

    async def send_signal_alert(self, signal: dict):
        if not self.bot or not self.chat_id:
            return

        direction_icon = "🟢 LONG" if signal['direction'] == 'LONG' else "🔴 SHORT"
        
        message = (
            f"⚡ **APEX SIGNAL ALERT** ⚡\n\n"
            f"**Asset:** {signal['symbol']}\n"
            f"**Action:** {direction_icon}\n"
            f"**Confidence:** {signal['confidence']}/100\n\n"
            f"🎯 **Entry:** {signal['entry']}\n"
            f"🛑 **Stop Loss:** {signal['stop_loss']}\n"
            f"💰 **Take Profit:** {signal['take_profit']}\n\n"
            f"🕒 {signal['timestamp']}"
        )

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='Markdown')
        except NetworkError:
            print(f"[Telegram] Network dropped while sending alert for {signal['symbol']}.")
        except Exception as e:
            print(f"[Telegram] Failed to send alert: {e}")

    def run_polling(self):
        if self.app:
            print("Starting Telegram Bot listener...")
            # We add drop_pending_updates so it doesn't process old commands if it goes offline
            self.app.run_polling(drop_pending_updates=True)