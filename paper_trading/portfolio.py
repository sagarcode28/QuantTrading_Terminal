# paper_trading/portfolio.py
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

class PaperTrader:
    def __init__(self):
        self.initial_balance = config.PAPER_TRADING_BALANCE
        self.current_balance = self.initial_balance
        self.open_positions = {}  # Active trades
        self.trade_history = []   # Closed trades

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """
        Calculates position size based on a strict 1% account risk model.
        """
        risk_amount = self.current_balance * config.RISK_PER_TRADE_PCT
        price_distance = abs(entry_price - stop_loss)
        
        if price_distance == 0:
            return 0
            
        # Quantity = Amount at risk / Risk per unit
        quantity = risk_amount / price_distance
        return quantity

    def execute_signal(self, signal: dict):
        """Processes an approved signal into an open virtual position."""
        if signal.get('status') != 'approved':
            return False

        symbol = signal['symbol']
        if symbol in self.open_positions:
            print(f"Position already open for {symbol}. Ignoring signal.")
            return False

        qty = self.calculate_position_size(signal['entry'], signal['stop_loss'])
        cost_basis = qty * signal['entry']

        if cost_basis > self.current_balance:
            print(f"Insufficient virtual funds for {symbol} trade.")
            return False

        trade_record = {
            'trade_id': f"TRD-{int(datetime.utcnow().timestamp())}",
            'symbol': symbol,
            'direction': signal['direction'],
            'entry_price': signal['entry'],
            'quantity': qty,
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'status': 'OPEN',
            'open_time': signal['timestamp']
        }

        self.open_positions[symbol] = trade_record
        print(f"[PAPER EXECUTION] Opened {signal['direction']} on {symbol} | Entry: {signal['entry']} | Qty: {round(qty, 4)}")
        return True

    def update_positions(self, current_prices: dict):
        """
        Polls open positions against the live price stream to trigger SL or TP.
        current_prices format: {'BTC/USDT': 65000.50, ...}
        """
        closed_this_tick = []
        
        for symbol, trade in self.open_positions.items():
            current_price = current_prices.get(symbol)
            if not current_price:
                continue

            close_trade = False
            pnl = 0

            # Check Longs
            if trade['direction'] == 'LONG':
                if current_price <= trade['stop_loss']:
                    close_trade, reason = True, 'SL Hit'
                elif current_price >= trade['take_profit']:
                    close_trade, reason = True, 'TP Hit'
                
                if close_trade:
                    pnl = (current_price - trade['entry_price']) * trade['quantity']

            # Check Shorts
            elif trade['direction'] == 'SHORT':
                if current_price >= trade['stop_loss']:
                    close_trade, reason = True, 'SL Hit'
                elif current_price <= trade['take_profit']:
                    close_trade, reason = True, 'TP Hit'
                
                if close_trade:
                    pnl = (trade['entry_price'] - current_price) * trade['quantity']

            if close_trade:
                trade['close_price'] = current_price
                trade['close_time'] = datetime.utcnow().isoformat()
                trade['pnl'] = pnl
                trade['status'] = 'CLOSED'
                trade['close_reason'] = reason
                
                self.current_balance += pnl
                self.trade_history.append(trade)
                closed_this_tick.append(symbol)
                
                print(f"[TRADE CLOSED] {symbol} {reason} | PnL: {round(pnl, 2)} USDT | New Balance: {round(self.current_balance, 2)}")

        # Clean up open positions dictionary
        for symbol in closed_this_tick:
            del self.open_positions[symbol]