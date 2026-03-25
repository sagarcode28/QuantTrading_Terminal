# smc_engine/structure.py
import pandas as pd
import numpy as np

class SMCEngine:
    @staticmethod
    def identify_fvgs(df: pd.DataFrame) -> pd.DataFrame:
        """
        Identifies Fair Value Gaps (Imbalances).
        Bullish FVG: Low of candle 3 is higher than High of candle 1.
        Bearish FVG: High of candle 3 is lower than Low of candle 1.
        """
        df['fvg_bullish'] = False
        df['fvg_bearish'] = False
        
        # Bullish FVG
        condition_bullish = (df['low'] > df['high'].shift(2)) & (df['close'].shift(1) > df['open'].shift(1))
        df.loc[condition_bullish, 'fvg_bullish'] = True
        
        # Bearish FVG
        condition_bearish = (df['high'] < df['low'].shift(2)) & (df['close'].shift(1) < df['open'].shift(1))
        df.loc[condition_bearish, 'fvg_bearish'] = True
        
        return df

    @staticmethod
    def map_structure(df: pd.DataFrame, lookback: int = 5, lookforward: int = 5) -> pd.DataFrame:
        """
        Maps basic market structure by identifying Swing Highs and Swing Lows.
        """
        df['swing_high'] = False
        df['swing_low'] = False
        
        for i in range(lookback, len(df) - lookforward):
            # Check for Swing High
            if df['high'].iloc[i] == max(df['high'].iloc[i-lookback:i+lookforward+1]):
                df.iloc[i, df.columns.get_loc('swing_high')] = True
                
            # Check for Swing Low
            if df['low'].iloc[i] == min(df['low'].iloc[i-lookback:i+lookforward+1]):
                df.iloc[i, df.columns.get_loc('swing_low')] = True
                
        return df