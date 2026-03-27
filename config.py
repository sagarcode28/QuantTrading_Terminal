# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # --- API Credentials ---
    DELTA_API_KEY = os.getenv("DELTA_API_KEY", "your_api_key_here")
    DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "your_api_secret_here")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # --- Trading Parameters ---
    EXCHANGE_ID = 'bitget'
    SYMBOLS = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"
    ]  # Assets to monitor
    TIMEFRAMES = {
        'entry': '15m',
        'structure': '1h',
        'trend': '4h'
    }
    
    # --- Execution Settings ---
    TRADING_MODE = "PAPER"  # Can be "PAPER" or "LIVE"
    DELTA_API_KEY = os.getenv("DELTA_API_KEY", "")
    DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "")

    # --- Risk Management ---
    PAPER_TRADING_BALANCE = 10000.0  # USDT
    RISK_PER_TRADE_PCT = 0.01        # 1% risk per trade
    MAX_TRADES_PER_DAY = 5

    # --- RISK MANAGEMENT UPGRADES ---
    TRAILING_ACTIVATION_PCT = 0.015  # Start trailing once trade is 1.5% in profit
    TRAILING_DISTANCE_PCT = 0.01     # Trail the peak price by 1.0%
    
    # --- Optimized Strategy Parameters ---
    MIN_CONFIDENCE_SCORE = 60        # Lowered from 70 to capture more valid SMC setups
    DEFAULT_RR_RATIO = 1.0           # 1:1 Risk/Reward optimized for 15m crypto timeframe

    # --- Portfolio Management ---
    HOUSE_MONEY_MULTIPLIER = 2.0  # Alerts when account doubles (e.g., 5000 -> 10000)
    
    # --- Database ---
    # Using SQLite for local dev, structured for easy Postgres migration later
    DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'apex_trading.db')
    DATABASE_URI = f"sqlite:///{DB_PATH}"

config = Config()