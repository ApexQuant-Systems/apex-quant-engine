import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.regime_classifier import RegimeEngine
from structure_engine.swing_detector import StructureEngine
from core.scoring_engine import ScoringEngine

class HistoricalTruthMachine:
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
        entry_price, stop_loss, take_profit, position_size = 0, 0, 0, 0
        is_at_breakeven = False
        
        for index, row in df.iterrows():
            if self.in_trade:
                # 1. BREAK-EVEN TRIGGER: If profit >= 1R, move stop to entry
                if not is_at_breakeven and row['high'] >= (entry_price + (entry_price - stop_loss)):
                    stop_loss = entry_price
                    is_at_breakeven = True
                
                # 2. EXIT LOGIC
                if row['low'] <= stop_loss: 
                    self.capital -= (entry_price - stop_loss) * position_size
                    losses += 1
                    self.in_trade = False
                elif row['high'] >= take_profit: 
                    self.capital += (take_profit - entry_price) * position_size
                    wins += 1
                    self.in_trade = False
                continue
            
            # 3. ENTRY LOGIC
            if row.get('Trade_Authorized', False):
                entry_price = row['close']
                stop_loss = entry_price * 0.98
                take_profit = entry_price + ((entry_price - stop_loss) * 4.0)
                position_size = (self.capital * self.risk_pct) / (entry_price - stop_loss)
                self.in_trade = True
                is_at_breakeven = False
                execs += 1
        
        print(f"\n--- TRUTH MACHINE REPORT (BE UPGRADED) ---")
        print(f"Executions: {execs} | Win Rate: {(wins/(wins+losses)*100) if (wins+losses)>0 else 0:.1f}%")
        print(f"Final Capital: ${self.capital:,.2f}")

if __name__ == "__main__":
    tester = HistoricalTruthMachine()
    tester.run_backtest('data/BTC_USDT_1h.csv')
