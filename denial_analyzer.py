import sqlite3
import os
import sys
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "storage", "apex_systems.db")

class DenialAnalyticsEngine:
    """Initializes and processes filter efficiency data for all rejected structural setups."""
    def __init__(self):
        self.db_path = DB_PATH
        self._bootstrap_denial_schema()

    def _bootstrap_denial_schema(self):
        """Creates the permanent denial database space without touching the trade journal table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS denial_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                regime TEXT NOT NULL,
                displacement_ratio REAL NOT NULL,
                conviction_score INTEGER NOT NULL,
                denial_reason TEXT NOT NULL,
                price_at_denial REAL NOT NULL,
                outcome_price_30m REAL,
                outcome_price_4h REAL
            )
        """)
        conn.commit()
        conn.close()

    def log_denied_signal(self, symbol, regime, displacement, score, reason, price):
        """Invoked by workers to record an infrastructure or logical rejection event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO denial_ledger (
                symbol, timestamp, regime, displacement_ratio, conviction_score, denial_reason, price_at_denial
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (symbol, timestamp, regime, displacement, score, reason, price))
        conn.commit()
        conn.close()
        print(f"[💾 LOGGED] Centralized denial ledger updated for {symbol} | Reason: {reason}")

    def generate_efficiency_report(self):
        """Computes statistical metrics determining if filters are protecting capital or suffocating edge."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM denial_ledger", conn)
        conn.close()

        print("\n==================================================")
        print("   APEX SYSTEMS: DENIAL MINING INTELLIGENCE MAP   ")
        print("==================================================")
        
        if df.empty:
            print("[-] Ledger Clean Room Space Pristine: Awaiting forward denial logs.")
            print("==================================================\n")
            return

        total_denials = len(df)
        print(f" [*] Total Operational Denials Logged: {total_denials}")
        print("--------------------------------------------------")
        
        print(" BY-REASON ATTRIBUTION ANALYSIS:")
        for reason, group in df.groupby('denial_reason'):
            percentage = (len(group) / total_denials) * 100
            print(f" ├── [{percentage:.1f}%] {reason} ({len(group)} instances)")
            
        print("--------------------------------------------------")
        print(" BY-REGIME FILTRATION PROFILE:")
        for regime, group in df.groupby('regime'):
            print(f" └── {regime:<16} : {len(group)} setups rejected")
        print("==================================================\n")

if __name__ == "__main__":
    analyzer = DenialAnalyticsEngine()
    
    # Run structural integration audit with sample mock denial inputs
    print("[*] Running network test verification queries...")
    analyzer.log_denied_signal("SOLUSDT", "HIGH_COMPRESSION", 0.42, 45, "Displacement filter minimum threshold failure", 132.40)
    analyzer.log_denied_signal("BTCUSDT", "EXPANSION_BEAR", 1.85, 65, "Portfolio Max Risk Ceiling Block", 76450.00)
    analyzer.log_denied_signal("ETHUSDT", "CHOCCY_COMPRESSION", 0.12, 20, "Low conviction scoring matrix denial", 2640.00)
    
    # Generate the analytics readout directly from the fresh disk lines
    analyzer.generate_efficiency_report()
