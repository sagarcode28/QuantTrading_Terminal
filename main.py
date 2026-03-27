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
            # Fetch the last 200 candles to ensure EMAs calculate correctly
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

    def update_trailing_stops(self, symbol, current_price):
        """
        Dynamically adjusts the stop loss as the price moves in our favor.
        """
        position = self.open_positions[symbol]
        direction = position.get('direction', 'LONG')
        # Safely grab the entry price
        entry_price = position.get('entry') 
        current_sl = position['stop_loss']
        
        if 'peak_price' not in position:
            position['peak_price'] = entry_price

        updated = False

        if direction == 'LONG':
            if current_price > position['peak_price']:
                position['peak_price'] = current_price
            
            profit_pct = (position['peak_price'] - entry_price) / entry_price
            
            if profit_pct >= config.TRAILING_ACTIVATION_PCT:
                new_sl = position['peak_price'] * (1 - config.TRAILING_DISTANCE_PCT)
                if new_sl > current_sl:
                    self.open_positions[symbol]['stop_loss'] = new_sl
                    updated = True
                    print(f"🛡️ [RISK MGMT] {symbol} Trailing Stop moved UP to {new_sl:.4f}")

        elif direction == 'SHORT':
            if current_price < position['peak_price']:
                position['peak_price'] = current_price
            
            profit_pct = (entry_price - position['peak_price']) / entry_price
            
            if profit_pct >= config.TRAILING_ACTIVATION_PCT:
                new_sl = position['peak_price'] * (1 + config.TRAILING_DISTANCE_PCT)
                if new_sl < current_sl:
                    self.open_positions[symbol]['stop_loss'] = new_sl
                    updated = True
                    print(f"🛡️ [RISK MGMT] {symbol} Trailing Stop moved DOWN to {new_sl:.4f}")

        if updated:
            self.state_manager.update_positions(self.open_positions)

    async def run(self):
        print("\n🚀 Apex Live Execution Engine Started.")
        await self.alerter.send_alert("🤖 *Apex Terminal Online*\nLive Market Polling Initiated.")
        
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}] Polling Markets...")
                
                # ==========================================
                # 1. FETCH DATA FOR ALL COINS
                # ==========================================
                latest_data = {}
                for symbol in config.SYMBOLS:
                    df = await self.fetch_latest_data(symbol)
                    if not df.empty and len(df) >= 200:
                        latest_data[symbol] = df
                
                if not latest_data:
                    print("⚠️ Network Timeout: Failed to fetch data. Retrying in 60 seconds.")
                    await asyncio.sleep(60)
                    continue

                # ==========================================
                # 2. POSITION MANAGEMENT (TRAILING STOPS & EXITS)
                # ==========================================
                for symbol in list(self.open_positions.keys()):
                    if symbol not in latest_data:
                        continue
                        
                    # Get the absolute current live price
                    current_price = latest_data[symbol].iloc[-1]['close'] 
                    
                    # Update trailing stops mathematically
                    self.update_trailing_stops(symbol, current_price)
                    
                    position = self.open_positions[symbol]
                    direction = position.get('direction', 'LONG')
                    
                    exit_triggered = False
                    exit_reason = ""
                    
                    # Check for Stop Loss or Take Profit
                    if direction == 'LONG':
                        if current_price <= position['stop_loss']:
                            exit_triggered = True
                            exit_reason = "🛑 STOP LOSS / TRAILING STOP HIT"
                        elif current_price >= position['take_profit']:
                            exit_triggered = True
                            exit_reason = "🎯 TAKE PROFIT HIT"
                            
                    elif direction == 'SHORT':
                        if current_price >= position['stop_loss']:
                            exit_triggered = True
                            exit_reason = "🛑 STOP LOSS / TRAILING STOP HIT"
                        elif current_price <= position['take_profit']:
                            exit_triggered = True
                            exit_reason = "🎯 TAKE PROFIT HIT"

                    # Execute the Exit
                    if exit_triggered:
                        print(f"[{current_time.strftime('%H:%M:%S')}] {exit_reason} for {symbol} at {current_price}")
                        await self.alerter.send_alert(f"🔔 **TRADE CLOSED** 🔔\nAsset: {symbol}\nReason: {exit_reason}\nExit Price: ${current_price}")
                        
                        # Remove from local memory and sync to MongoDB
                        del self.open_positions[symbol]
                        self.state_manager.update_positions(self.open_positions)

                # ==========================================
                # 3. SCAN FOR NEW TRADE SETUPS
                # ==========================================
                for symbol in config.SYMBOLS:
                    if symbol in self.open_positions or symbol not in latest_data:
                        continue
                        
                    df = latest_data[symbol]
                    # Get absolute most recent completed candle (index -2)
                    latest_candle = df.iloc[-2] 
                    
                    # Run your original Signal Generator
                    signal = self.generator.generate(
                        symbol=symbol, 
                        latest_data=latest_candle, 
                        mtf_alignment=True, 
                        candle_time=None 
                    )
                    
                    if signal.get('status') == 'approved':
                        entry = signal['entry']
                        sl = signal['stop_loss']
                        tp = signal['take_profit']
                        direction = signal['direction']
                        
                        # Save the trade and sync to MongoDB Cloud
                        self.open_positions[symbol] = signal
                        self.state_manager.update_positions(self.open_positions)
                        
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

                # Check Milestones
                await self.check_milestone()
                
                # Sleep for 15 minutes
                print("💤 Cycle complete. Hibernating for 15 minutes...")
                await asyncio.sleep(895) 
                
            except Exception as e:
                error_msg = f"⚠️ [CRITICAL ERROR] Execution Loop Exception: {e}"
                print(error_msg)
                print("🔄 Auto-recovering. Restarting loop in 60 seconds...")
                await asyncio.sleep(60)

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