import sqlite3
import pandas as pd
import sys
import os

# Add project root to path so we can import 'config'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.global_config import GLOBAL_CONFIG

class AnalyticsEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def calculate_stats(self):
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM trade_ledger", conn)
        conn.close()
        
        if df.empty:
            return "No trades recorded."
            
        total_trades = len(df)
        wins = len(df[df['status'] == 'PENDING']) 
        winrate = (wins / total_trades) * 100
        
        print(f"--- Performance Report ---")
        print(f"Total Trades: {total_trades}")
        print(f"Winrate: {winrate:.2f}%")
        print(f"--------------------------")

if __name__ == "__main__":
    engine = AnalyticsEngine(GLOBAL_CONFIG.db_path)
    engine.calculate_stats()
