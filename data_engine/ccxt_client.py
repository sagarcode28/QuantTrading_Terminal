# data_engine/ccxt_client.py
import ccxt
import pandas as pd
import time
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from database.db_handler import db

class DeltaExchangeClient:
    def __init__(self):
        # Initialize CCXT instance for Delta Exchange
        self.exchange = ccxt.delta({
            'apiKey': config.DELTA_API_KEY,
            'secret': config.DELTA_API_SECRET,
            'enableRateLimit': True, # Crucial for production to prevent IP bans
        })
        
    def fetch_historical_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """
        Fetches historical OHLCV data from Delta Exchange and returns a formatted DataFrame.
        """
        try:
            print(f"Fetching {limit} candles for {symbol} on {timeframe} timeframe...")
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                return pd.DataFrame()
                
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Save to database immediately upon fetching
            db.save_ohlcv_batch(df, symbol, timeframe)
            
            df.set_index('timestamp', inplace=True)
            return df
            
        except ccxt.NetworkError as e:
            print(f"Network error fetching data for {symbol}: {e}")
        except ccxt.ExchangeError as e:
            print(f"Exchange error fetching data for {symbol}: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            
        return pd.DataFrame()

    def sync_market_data(self):
        """Utility to pull the latest data for all configured symbols and timeframes."""
        for symbol in config.SYMBOLS:
            for tf_name, timeframe in config.TIMEFRAMES.items():
                self.fetch_historical_ohlcv(symbol, timeframe, limit=500)
                time.sleep(1) # Be polite to the exchange API

if __name__ == "__main__":
    # Quick test execution
    client = DeltaExchangeClient()
    client.sync_market_data()
    print("Market data sync complete.")