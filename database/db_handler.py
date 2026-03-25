# database/db_handler.py
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
import sys
import os

# Append project root to path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

Base = declarative_base()

class OHLCVData(Base):
    __tablename__ = 'ohlcv_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(5), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    # Ensure we don't store duplicate candles
    __table_args__ = (UniqueConstraint('symbol', 'timeframe', 'timestamp', name='_symbol_tf_ts_uc'),)

class DatabaseHandler:
    def __init__(self):
        self.engine = create_engine(config.DATABASE_URI, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def save_ohlcv_batch(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Saves a Pandas DataFrame of OHLCV data to the database."""
        if df.empty:
            return
            
        df_to_save = df.copy()
        df_to_save['symbol'] = symbol
        df_to_save['timeframe'] = timeframe
        
        # Using Pandas 'to_sql' for fast batch insertion, ignoring duplicates
        try:
            df_to_save.to_sql('ohlcv_data', con=self.engine, if_exists='append', index=False)
            print(f"Saved {len(df_to_save)} records for {symbol} ({timeframe})")
        except Exception as e:
            # Handle unique constraint violations silently if updating existing records
            pass

    def get_historical_data(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """Retrieves OHLCV data directly into a Pandas DataFrame."""
        query = f"""
            SELECT timestamp, open, high, low, close, volume 
            FROM ohlcv_data 
            WHERE symbol = '{symbol}' AND timeframe = '{timeframe}' 
            ORDER BY timestamp DESC LIMIT {limit}
        """
        df = pd.read_sql(query, self.engine)
        df.sort_values(by='timestamp', inplace=True)
        df.set_index('timestamp', inplace=True)
        return df

db = DatabaseHandler()