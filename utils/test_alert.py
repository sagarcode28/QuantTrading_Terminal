# utils/test_alert.py
import asyncio
import sys
import os
from datetime import datetime

# Append project root to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from telegram_bot.bot import TelegramAlerter

async def send_mock_signal():
    print("Initializing Telegram Alerter...")
    alerter = TelegramAlerter()
    
    # Create a fake, highly profitable looking signal
    mock_signal = {
        'symbol': 'SOL/USDT',
        'direction': 'LONG',
        'entry': 145.50,
        'stop_loss': 143.00,
        'take_profit': 148.00, # 1:1 RR based on our new optimized config
        'confidence': 88,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    print("Pushing mock signal to Telegram...")
    await alerter.send_signal_alert(mock_signal)
    print("✅ Alert sent! Check your phone.")

if __name__ == "__main__":
    # Run the async function
    asyncio.run(send_mock_signal())