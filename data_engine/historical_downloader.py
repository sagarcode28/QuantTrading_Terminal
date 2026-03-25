# data_engine/historical_downloader.py
import ccxt
import pandas as pd
import time
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from database.db_handler import db

class DeepHistoryDownloader:
    def __init__(self):
        # Switch to Binance for maximum historical data depth
        self.exchange = ccxt.binance({'enableRateLimit': True})

    def download_max_history(self, symbol: str, timeframe: str):
        print(f"\n🚀 Initiating DEEP historical sync for {symbol} ({timeframe})...")
        
        # Set start date to Jan 1, 2017 (Dawn of USDT pairs)
        start_date = datetime(2017, 1, 1, tzinfo=timezone.utc)
        since = self.exchange.parse8601(start_date.isoformat().replace('+00:00', 'Z'))
        now = self.exchange.milliseconds()
        
        all_ohlcv = []
        retries = 0
        max_retries = 3
        
        while since < now:
            try:
                # Binance allows 1000 candles per request
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
                
                if not ohlcv:
                    print(f"🏁 Reached present day for {symbol}.")
                    break
                    
                all_ohlcv.extend(ohlcv)
                
                # Update 'since' to the timestamp of the last candle + 1ms
                last_ts = ohlcv[-1][0]
                since = last_ts + 1
                
                # Print progress to console
                current_date = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
                print(f"Fetched {len(all_ohlcv)} candles... Currently at: {current_date}", end='\r')
                
                time.sleep(0.5)  # Respect Binance API rate limits
                retries = 0 
                
            except ccxt.BadSymbol:
                print(f"\n❌ ERROR: Binance does not support the symbol '{symbol}'. Skipping...")
                return 
                
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    print(f"\n⚠️ Max retries reached for {symbol}. Moving on.")
                    break
                print(f"\nError: {e}. Retrying {retries}/{max_retries} in 5 seconds...")
                time.sleep(5)
                
        print() # Clear the carriage return line
        
        if all_ohlcv:
            # Drop duplicates just in case of API overlap
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df.drop_duplicates(subset=['timestamp'], inplace=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Save to SQLite
            db.save_ohlcv_batch(df, symbol, timeframe)
            print(f"✅ Successfully archived {len(df)} total candles for {symbol}.")
        else:
            print(f"⚠️ No data fetched for {symbol}.")

if __name__ == "__main__":
    downloader = DeepHistoryDownloader()
    
    try:
        downloader.exchange.load_markets()
    except Exception as e:
        print(f"Could not load markets: {e}")
    
    print("WARNING: This will pull hundreds of thousands of candles and may take several minutes per coin.")
    
    for symbol in config.SYMBOLS:
        downloader.download_max_history(symbol, '15m')
        
    print("\n🎉 Massive historical data sync complete. Your engine is now loaded with multi-year data.")