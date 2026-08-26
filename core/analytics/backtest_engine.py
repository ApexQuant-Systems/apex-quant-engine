import sqlite3
import pandas as pd
from core.market_intelligence import IntelligenceEngine
from core.strategy_engine import StrategyEngine
# ... (imports)

class BacktestEngine:
    # ... (init code)

    def run(self, symbol: str):
        # Fetch 3 dimensions
        timeframes = {'HTF': '4h', 'MTF': '1h', 'LTF': '15m'}
        states = {}
        
        conn = sqlite3.connect(GLOBAL_CONFIG.db_path)
        for name, tf in timeframes.items():
            df = pd.read_sql_query(f"SELECT * FROM market_data WHERE symbol='{symbol}' AND timeframe='{tf}' ORDER BY timestamp ASC", conn)
            df = df.set_index(pd.to_datetime(df['timestamp'], unit='ms'))
            states[name] = self.intelligence.calculate_intelligence(df.iloc[-20:])
        conn.close()

        # The "Brain" now sees 3 dimensions
        signal = self.strategy.generate_signal(states['HTF'], states['MTF'], states['LTF'])
        return signal.action
