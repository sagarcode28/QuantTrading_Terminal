# ta_engine/indicators.py
import pandas as pd
import numpy as np
import talib

class TAEngine:
    @staticmethod
    def apply_all(df: pd.DataFrame) -> pd.DataFrame:
        """Applies core TA indicators to the dataframe."""
        if df.empty or len(df) < 200:
            return df

        # EMAs for Trend Detection
        df['vol_sma_20'] = df['volume'].rolling(window=20).mean()
        df['ema_20'] = talib.EMA(df['close'], timeperiod=20)
        df['ema_50'] = talib.EMA(df['close'], timeperiod=50)
        df['ema_200'] = talib.EMA(df['close'], timeperiod=200)

        # Momentum & Volatility
        df['rsi_14'] = talib.RSI(df['close'], timeperiod=14)
        df['atr_14'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
        # ADX for Trend Strength (Values > 25 indicate strong trend)
        df['adx_14'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        
        # Volume Moving Average
        df['volume_ma_20'] = talib.SMA(df['volume'], timeperiod=20)

        # Basic Trend Classification
        df['ta_trend'] = np.where(
            (df['close'] > df['ema_50']) & (df['ema_50'] > df['ema_200']), 'bullish',
            np.where((df['close'] < df['ema_50']) & (df['ema_50'] < df['ema_200']), 'bearish', 'neutral')
        )
        
        return df