import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.regime_classifier import RegimeEngine
from structure_engine.swing_detector import StructureEngine
from core.scoring_engine import ScoringEngine

class PartialProfitTester:
    def __init__(self, initial_capital=10000.0, risk_pct=0.01):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_pct = risk_pct
        self.in_trade = False
        
    def run_backtest(self, csv_path):
        df = pd.read_csv(csv_path)
        regime = RegimeEngine()
        scorer = ScoringEngine()
        structure = StructureEngine(lookback=5)
        
        df = regime.classify_market_regime(df)
        df = structure.detect_swings(df)
        df = scorer.score_displacement(df)
        
        wins, losses, execs = 0, 0, 0
        entry_price, stop_loss, position_size = 0, 0, 0
        tp_partial, tp_full = 0, 0
        has_taken_partial = False
        
        for index, row in df.iterrows():
            if self.in_trade:
                # 1. PARTIAL TAKE PROFIT (50% at 2R)
                if not has_taken_partial and row['high'] >= tp_partial:
                    profit = (tp_partial - entry_price) * (position_size * 0.5)
                    self.capital += profit
                    position_size *= 0.5 # Halve position
                    stop_loss = entry_price # Move stop to BE
                    has_taken_partial = True
                
                # 2. FINAL EXIT (Full close at 4R)
                if row['high'] >= tp_full:
                    profit = (tp_full - entry_price) * position_size
                    self.capital += profit
                    wins += 1
                    self.in_trade = False
                elif row['low'] <= stop_loss:
                    loss = (entry_price - stop_loss) * position_size
                    self.capital -= loss
                    losses += 1
                    self.in_trade = False
                continue
            
            # 3. ENTRY
            if row.get('Trade_Authorized', False):
                entry_price = row['close']
                stop_loss = entry_price * 0.98
                risk_dist = entry_price - stop_loss
                tp_partial = entry_price + (risk_dist * 2.0)
                tp_full = entry_price + (risk_dist * 4.0)
                position_size = (self.capital * self.risk_pct) / risk_dist
                self.in_trade = True
                has_taken_partial = False
                execs += 1
        
        print(f"\n--- PARTIAL PROFIT EXPERIMENT ---")
        print(f"Executions: {execs} | Final Capital: ${self.capital:,.2f}")

if __name__ == "__main__":
    tester = PartialProfitTester()
    tester.run_backtest('data/BTC_USDT_1h.csv')
