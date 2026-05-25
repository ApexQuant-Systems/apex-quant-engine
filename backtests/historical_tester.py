import pandas as pd
import sys
import os

# Path corrections MUST occur prior to local module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.regime_classifier import RegimeEngine
from structure_engine.swing_detector import StructureEngine
from core.scoring_engine import ScoringEngine
from infrastructure.logger import QuantLogger

class HistoricalTruthMachine:
    def __init__(self, initial_capital=10000.0, risk_pct=0.01):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_pct = risk_pct
        self.in_trade = False
        self.log = QuantLogger()
        
    def run_backtest(self, csv_path):
        self.log.log(f"--- INITIALIZING HISTORICAL RUN: {csv_path} ---")
        df = pd.read_csv(csv_path)
        
        regime = RegimeEngine()
        scorer = ScoringEngine()
        structure = StructureEngine(lookback=5)
        
        df = regime.classify_market_regime(df)
        df = structure.detect_swings(df)
        df = scorer.score_displacement(df)
        
        wins, losses, execs = 0, 0, 0
        entry_price, stop_loss, take_profit, position_size = 0, 0, 0, 0
        
        for index, row in df.iterrows():
            if self.in_trade:
                if row['low'] <= stop_loss:
                    self.capital -= (entry_price - stop_loss) * position_size
                    losses += 1
                    self.in_trade = False
                elif row['high'] >= take_profit:
                    self.capital += (take_profit - entry_price) * position_size
                    wins += 1
                    self.in_trade = False
                continue
            
            if row.get('Trade_Authorized', False):
                entry_price = row['close']
                stop_loss = entry_price * 0.98
                take_profit = entry_price + ((entry_price - stop_loss) * 4.0)
                
                risk_dist = entry_price - stop_loss
                position_size = (self.capital * self.risk_pct) / risk_dist
                
                self.in_trade = True
                execs += 1

        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
        
        self.log.log("\n==============================================")
        self.log.log("      PRODUCTION BASELINE ALPHA REPORT v1.0   ")
        self.log.log("==============================================")
        self.log.log(f"Total Executions : {execs}")
        self.log.log(f"Win Rate         : {win_rate:.1f}%")
        self.log.log(f"Final Capital    : ${self.capital:,.2f}")
        self.log.log("==============================================\n")

if __name__ == "__main__":
    tester = HistoricalTruthMachine()
    tester.run_backtest('data/BTC_USDT_1h.csv')
