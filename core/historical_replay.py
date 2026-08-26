# filename: core/historical_replay.py
import sqlite3
import pandas as pd
from core.market_intelligence import IntelligenceEngine
from core.strategy_engine import StrategyEngine
from config.global_config import GLOBAL_CONFIG

class HistoricalReplay:
    def __init__(self):
        self.engine = IntelligenceEngine()
        self.strategy = StrategyEngine()
        self.db_path = GLOBAL_CONFIG.db_path

    def run_replay(self, symbol: str, timeframe: str):
        conn = sqlite3.connect(self.db_path)
        # Fetch all stored data for the symbol/timeframe
        query = f"SELECT * FROM market_data WHERE symbol='{symbol}' AND timeframe='{timeframe}' ORDER BY timestamp ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return "NO_DATA"

        # Replay loop: Feed rows to the Intelligence Engine
        # (For V1, we simulate the HTF/MTF/LTF context)
        state = self.engine.calculate_intelligence(df)
        signal = self.strategy.generate_signal(state, state, state)
        
        return signal.action

if __name__ == "__main__":
    replay = HistoricalReplay()
    result = replay.run_replay("BTCUSDT", "1h")
    print(f"[REPLAY RESULT] Signal generated: {result}")
