# main.py
import asyncio
import ccxt
import pandas as pd
from datetime import datetime, timezone
import time
import sys
import os

from flask import Flask
import threading

# Internal Modules
from config import config
from database.db_handler import db
from ta_engine.indicators import TAEngine
from signal_engine.generator import SignalGenerator
from telegram_bot.alerter import TelegramAlerter
from news_engine.analyzer import MarketSentiment
from database.state_manager import StateManager

class LiveExecutionEngine:
    def __init__(self):
        self.alerter = TelegramAlerter()
        self.generator = SignalGenerator()
        
        # Initialize Exchange
        if config.TRADING_MODE == "LIVE" and config.DELTA_API_KEY:
            self.exchange = ccxt.delta({
                'apiKey': config.DELTA_API_KEY,
                'secret': config.DELTA_API_SECRET,
                'enableRateLimit': True
            })
            print("🔴 WARNING: LIVE TRADING MODE ENGAGED. REAL CAPITAL AT RISK.")
        else:
            self.exchange = ccxt.delta({'enableRateLimit': True})
            print("🟢 PAPER TRADING MODE ENGAGED. SIMULATED EXECUTION.")

        # Portfolio State (Cloud Memory)
        self.state_manager = StateManager()
        self.initial_capital = config.PAPER_TRADING_BALANCE
        
        # Load state from MongoDB
        state = self.state_manager.get_state()
        self.live_capital = state['live_capital']
        self.open_positions = state.get('open_positions', {})
        self.milestone_hit = state.get('milestone_hit', False)

    async def fetch_latest_data(self, symbol: str) -> pd.DataFrame:
        """Fetches the latest candles and applies TA logic."""
        try:
            # Fetch the last 200 candles to ensure EMAs (like 200 EMA) calculate correctly
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='15m', limit=200)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Apply all technical indicators
            df = TAEngine.apply_all(df)
            return df
        except Exception as e:
            print(f"⚠️ Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    async def check_milestone(self):
        """Checks if the House Money milestone has been reached."""
        # Use getattr to safely check config in case it wasn't added yet
        multiplier = getattr(config, 'HOUSE_MONEY_MULTIPLIER', 2.0)
        target = self.initial_capital * multiplier
        
        if self.live_capital >= target and not self.milestone_hit:
            msg = (
                f"🎉 **PORTFOLIO MILESTONE REACHED** 🎉\n\n"
                f"Account Equity: `${round(self.live_capital, 2)}`\n"
                f"Target Multiplier: `{multiplier}x`\n\n"
                f"💡 *Action Required:* It is now mathematically safe to withdraw your initial `${self.initial_capital}` risk. "
                f"You are officially trading with House Money!"
            )
            await self.alerter.send_alert(msg)
            print(f"\n[MILESTONE] {msg}\n")
            self.milestone_hit = True

    async def run(self):
        print("\n🚀 Apex Live Execution Engine Started.")
        await self.alerter.send_alert("🤖 *Apex Terminal Online*\nLive Market Polling Initiated.")
        
        while True:
            current_time = datetime.now(timezone.utc)
            print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}] Polling Markets...")
            
            for symbol in config.SYMBOLS:
                df = await self.fetch_latest_data(symbol)
                
                if df.empty or len(df) < 200:
                    continue
                
                # Get the absolute most recent completed candle (index -2 to avoid unclosed current candle)
                latest_candle = df.iloc[-2] 
                
                # Check for Signal
                signal = self.generator.generate(
                    symbol=symbol, 
                    latest_data=latest_candle, 
                    mtf_alignment=True, 
                    candle_time=None # None forces Live Mode (News Engine active)
                )
                
                if signal.get('status') == 'approved':
                    # Prevent duplicate trades if we are already in one
                    if symbol in self.open_positions:
                        continue 
                        
                    entry = signal['entry']
                    sl = signal['stop_loss']
                    tp = signal['take_profit']
                    direction = signal['direction']
                    
                    # Log the trade
                    self.open_positions[symbol] = signal
                    
                    alert_msg = (
                        f"⚡ **APEX EXECUTION ALERT** ⚡\n\n"
                        f"**Asset:** {symbol}\n"
                        f"**Action:** {direction}\n"
                        f"**Entry:** ${entry}\n"
                        f"**Stop Loss:** ${sl}\n"
                        f"**Take Profit:** ${tp}\n"
                        f"**Confidence:** {signal['confidence']}/100\n"
                        f"**Mode:** {config.TRADING_MODE}"
                    )
                    
                    print(f"✅ Executing {direction} on {symbol} at ${entry}")
                    await self.alerter.send_alert(alert_msg)
                    
                    # NOTE: If TRADING_MODE == 'LIVE', you would place the ccxt.create_market_order() here
            
            # Check Portfolio Milestones
            await self.check_milestone()
            
            # The heart of the 15-minute engine. Sleep for 15 minutes (900 seconds)
            # We subtract a few seconds to ensure we hit the API right as the next candle closes.
            print("💤 Cycle complete. Hibernating for 15 minutes...")
            await asyncio.sleep(895) 

# --- DUMMY WEB SERVER FOR RENDER ---
app = Flask(__name__)

@app.route('/')
def keep_alive():
    return "Apex Terminal is Alive and Polling!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.start()
    
    engine = LiveExecutionEngine()
    
    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        print("\n🛑 Execution Engine Terminated by User.")
        sys.exit(0)