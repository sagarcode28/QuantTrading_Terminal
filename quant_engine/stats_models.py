# quant_engine/stats_models.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

class QuantEngine:
    @staticmethod
    def calculate_regime(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        Calculates a statistical regime score (-1 to 1).
        Positive = Uptrend/Expansion, Negative = Downtrend/Contraction.
        """
        if df.empty:
            return df
            
        # Log Returns
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # Realized Volatility (Annualized proxy for crypto intraday)
        df['realized_vol'] = df['log_return'].rolling(window=window).std() * np.sqrt(365 * 24 * 4)
        
        # Momentum Z-Score (Distance from mean in standard deviations)
        rolling_mean = df['close'].rolling(window=window).mean()
        rolling_std = df['close'].rolling(window=window).std()
        df['momentum_z_score'] = (df['close'] - rolling_mean) / rolling_std
        
        # Normalize Z-score to a 0-100 scale for the final signal engine
        scaler = MinMaxScaler(feature_range=(0, 100))
        # Fill NaNs temporarily for scaling, then put back
        temp_z = df['momentum_z_score'].fillna(0).values.reshape(-1, 1)
        df['quant_momentum_score'] = scaler.fit_transform(temp_z)
        
        return df