# signal_engine/scorer.py
import pandas as pd

class ConfluenceScorer:
    @staticmethod
    def calculate_score(row: pd.Series) -> dict:
        """
        Calculates a 0-100 confidence score based on multi-dimensional analysis.
        Returns a dictionary with the score and the identified direction.
        """
        score = 0
        direction = 'neutral'
        
        # 1. TA Trend Alignment (Max 30 points)
        if row.get('ta_trend') == 'bullish':
            score += 20
            direction = 'long'
            if row.get('adx_14', 0) > 25:  # Strong trend bonus
                score += 10
        elif row.get('ta_trend') == 'bearish':
            score += 20
            direction = 'short'
            if row.get('adx_14', 0) > 25:
                score += 10

        # 2. Quant Momentum (Max 25 points)
        quant_score = row.get('quant_momentum_score', 50)
        if direction == 'long' and quant_score > 70:
            score += 25
        elif direction == 'short' and quant_score < 30:
            score += 25
        elif 30 <= quant_score <= 70:
            score += 10 # Neutral momentum, partial points

        # 3. SMC Confirmation (Max 30 points)
        if direction == 'long' and (row.get('fvg_bullish') or row.get('swing_low')):
            score += 30
        elif direction == 'short' and (row.get('fvg_bearish') or row.get('swing_high')):
            score += 30

        # 4. Volume/Volatility Health (Max 15 points)
        if row.get('volume', 0) > row.get('volume_ma_20', float('inf')):
            score += 15 # Above average volume confirms the move

        return {
            'score': min(score, 100),  # Cap at 100
            'direction': direction if score >= 50 else 'neutral'
        }