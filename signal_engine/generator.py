# signal_engine/generator.py
import sys
import os
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from signal_engine.scorer import ConfluenceScorer
from news_engine.analyzer import MarketSentiment # <-- ADD THIS IMPORT

class SignalGenerator:
    def __init__(self):
        self.daily_signals_generated = 0
        self.last_reset_date = pd.Timestamp('2000-01-01').date()

    def generate(self, symbol: str, latest_data: pd.Series, mtf_alignment: bool, rr_ratio: float = config.DEFAULT_RR_RATIO, min_confidence: int = config.MIN_CONFIDENCE_SCORE, candle_time=None) -> dict:
        
        current_time = pd.to_datetime(candle_time) if candle_time else datetime.utcnow()
        current_date = current_time.date()

        if current_date > self.last_reset_date:
            self.daily_signals_generated = 0
            self.last_reset_date = current_date

        if self.daily_signals_generated >= config.MAX_TRADES_PER_DAY:
            return {'status': 'rejected', 'reason': 'Daily limit reached'}

        # Calculate Technical Confluence
        evaluation = ConfluenceScorer.calculate_score(latest_data)
        score = evaluation['score']
        direction = evaluation['direction']

        if score < min_confidence:
            return {'status': 'rejected', 'reason': f'Low confidence: {score}'}
        
        if not mtf_alignment:
            return {'status': 'rejected', 'reason': 'MTF 4H/1H/15m mismatch'}

        if direction == 'neutral':
            return {'status': 'rejected', 'reason': 'No directional bias'}

        # =========================================================
        # --- NEW: ANTI-EXHAUSTION FILTERS ---
        # =========================================================
        entry_price = latest_data['close']
        ema_20 = latest_data.get('ema_20', entry_price)
        ema_200 = latest_data.get('ema_200', entry_price)
        atr = latest_data.get('atr_14', entry_price * 0.01)

        # 1. Macro Trend Alignment (Only trade with the 200 EMA flow)
        if direction == 'long' and entry_price < ema_200:
            return {'status': 'rejected', 'reason': 'Counter Macro Trend (Below 200 EMA)'}
        if direction == 'short' and entry_price > ema_200:
            return {'status': 'rejected', 'reason': 'Counter Macro Trend (Above 200 EMA)'}

        # 2. Rubber Band Rule (Prevent entering overextended moves)
        # If price is more than 1.5 ATRs away from the 20 EMA, it is too late to enter safely.
        dist_from_ema20 = abs(entry_price - ema_20)
        if dist_from_ema20 > (atr * 1.5):
            return {'status': 'rejected', 'reason': 'Price Overextended (Mean Reversion Risk)'}

        # =========================================================
        # --- MACRO SENTIMENT FILTER (Live Trading Only) ---
        # =========================================================
        if candle_time is None: 
            sentiment = MarketSentiment.get_fear_and_greed()
            fgi_score = sentiment['score']
            
            print(f"🌍 [News Engine] Live Macro Sentiment: {fgi_score}/100 ({sentiment['classification']})")
            
            if direction == 'long' and fgi_score >= 80:
                print(f"⚠️ [News Engine] Blocked LONG on {symbol}. Market is in Extreme Greed.")
                return {'status': 'rejected', 'reason': f'Macro Block: Extreme Greed ({fgi_score})'}
                
            if direction == 'short' and fgi_score <= 20:
                print(f"⚠️ [News Engine] Blocked SHORT on {symbol}. Market is in Extreme Fear.")
                return {'status': 'rejected', 'reason': f'Macro Block: Extreme Fear ({fgi_score})'}
        # =========================================================

        # Calculate Execution Parameters (ATR-based Stop Loss)
        sl_distance = atr * 1.5 
        
        if direction == 'long':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * rr_ratio) 
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * rr_ratio) 

        self.daily_signals_generated += 1

        return {
            'status': 'approved',
            'symbol': symbol,
            'direction': direction.upper(),
            'entry': round(entry_price, 4),
            'stop_loss': round(stop_loss, 4),
            'take_profit': round(take_profit, 4),
            'confidence': score,
            'timestamp': current_time.isoformat()
        }