# backtest/optimizer.py
import sys
import os
import itertools
import pandas as pd
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.engine import BacktestEngine
from config import config

class GridOptimizer:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.engine = BacktestEngine(initial_capital=10000.0, risk_pct=0.01)
        
        # Define the parameter grid we want to test
        self.param_grid = {
            'rr_ratio': [1.0, 1.5, 2.0, 2.5, 3.0],      # Risk/Reward ratios
            'min_confidence': [60, 70, 75, 80]          # Signal strictness
        }

    def run_optimization(self):
        print(f"\n🚀 Starting Grid Search Optimization for {self.symbol}...")
        
        # Create all combinations of parameters
        keys, values = zip(*self.param_grid.items())
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        
        results_log = []
        total_runs = len(combinations)
        
        start_time = time.time()

        for idx, params in enumerate(combinations):
            print(f"⏳ Run {idx+1}/{total_runs} | RR: 1:{params['rr_ratio']} | Conf: {params['min_confidence']}")
            
            # Execute backtest with these specific parameters
            res = self.engine.run(
                symbol=self.symbol, 
                timeframe='15m', 
                rr_ratio=params['rr_ratio'], 
                min_confidence=params['min_confidence']
            )
            
            if "error" not in res:
                results_log.append({
                    'RR_Ratio': f"1:{params['rr_ratio']}",
                    'Min_Confidence': params['min_confidence'],
                    'Total_Trades': res['total_trades'],
                    'Win_Rate_%': res['win_rate'],
                    'Max_Drawdown_%': res['max_drawdown'],
                    'Net_Profit_$': res['net_profit']
                })

        # Process and rank results
        df_results = pd.DataFrame(results_log)
        
        if not df_results.empty:
            # Sort by Net Profit descending
            df_results = df_results.sort_values(by='Net_Profit_$', ascending=False).reset_index(drop=True)
            
            print(f"\n✅ Optimization Complete in {round(time.time() - start_time, 1)} seconds.")
            print(f"\n🏆 TOP 5 PARAMETER COMBINATIONS FOR {self.symbol}:")
            print("-" * 80)
            print(df_results.head(5).to_string(index=False))
            print("-" * 80)
        else:
            print("No valid results generated.")

if __name__ == "__main__":
    # Let's optimize SOL/USDT first
    optimizer = GridOptimizer(symbol="SOL/USDT")
    optimizer.run_optimization()