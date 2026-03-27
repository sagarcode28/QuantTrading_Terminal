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

    # V2 UPGRADE: Added 'macro_data' to the function parameters
    def generate(self, symbol: str, latest_data: pd.Series, macro_data: pd.Series = None, mtf_alignment: bool = True, rr_ratio: float = config.DEFAULT_RR_RATIO, min_confidence: int = config.MIN_CONFIDENCE_SCORE, candle_time=None) -> dict:
        
        current_time = pd.to_datetime(candle_time) if candle_time else datetime.utcnow()
        current_date = current_time.date()

        if current_date > self.last_reset_date:
            self.daily_signals_generated = 0
            self.last_reset_date = current_date

        if self.daily_signals_generated >= config.MAX_TRADES_PER_DAY:
            return {'status': 'rejected', 'reason': 'Daily limit reached'}

        # Calculate Technical Confluence (Using the 15m chart)
        evaluation = ConfluenceScorer.calculate_score(latest_data)
        score = evaluation['score']
        direction = evaluation['direction']

        if score < min_confidence:
            return {'status': 'rejected', 'reason': f'Low confidence: {score}'}
        
        if direction == 'neutral':
            return {'status': 'rejected', 'reason': 'No directional bias'}

        # =========================================================
        # --- NEW V2: MULTI-TIMEFRAME MACRO ALIGNMENT ---
        # =========================================================
        # We now check the 1-Hour chart to ensure the macro trend supports the 15m signal.
        if mtf_alignment and macro_data is not None:
            macro_close = macro_data['close']
            macro_ema_200 = macro_data.get('ema_200', macro_close)
            
            # If the 15m signal says LONG, but the 1H chart is trading below its 200 EMA, VETO.
            if direction == 'long' and macro_close < macro_ema_200:
                return {'status': 'rejected', 'reason': 'MTF Veto: 1H Macro Trend is Bearish'}
                
            # If the 15m signal says SHORT, but the 1H chart is trading above its 200 EMA, VETO.
            if direction == 'short' and macro_close > macro_ema_200:
                return {'status': 'rejected', 'reason': 'MTF Veto: 1H Macro Trend is Bullish'}

        # =========================================================
        # --- ANTI-EXHAUSTION FILTERS (15m Chart) ---
        # =========================================================
        entry_price = latest_data['close']
        ema_20 = latest_data.get('ema_20', entry_price)
        ema_200 = latest_data.get('ema_200', entry_price)
        atr = latest_data.get('atr_14', entry_price * 0.01)

        # 1. Local Trend Alignment (15m)
        if direction == 'long' and entry_price < ema_200:
            return {'status': 'rejected', 'reason': 'Counter Local Trend (Below 15m 200 EMA)'}
        if direction == 'short' and entry_price > ema_200:
            return {'status': 'rejected', 'reason': 'Counter Local Trend (Above 15m 200 EMA)'}

        # 2. Rubber Band Rule (Prevent entering overextended moves)
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