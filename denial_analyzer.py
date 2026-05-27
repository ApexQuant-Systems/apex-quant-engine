import sqlite3
import os
from pathlib import Path

DB_PATH = Path("./storage/apex_systems.db")

class DenialAnalyticsEngine:
    def __init__(self):
        # Ensure the storage directory exists natively
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes the structural ledger schema if it doesn't exist."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS denied_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                regime TEXT,
                displacement REAL,
                score REAL,
                reason TEXT,
                price REAL
            )
        """)
        conn.commit()
        conn.close()

    def log_denied_signal(self, symbol, regime, displacement, score, reason, price):
        """Persists a rejected execution signal into the cold-storage ledger."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO denied_signals (symbol, regime, displacement, score, reason, price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, str(regime), float(displacement), float(score), str(reason), float(price)))
            conn.commit()
        except Exception as e:
            print(f"[⚠️ LEDGER ERROR] Failed to write denial log: {e}")
        finally:
            conn.close()


def harvest_negative_space_metrics():
    """Extracts high-signal risk insights from the persistent database."""
    if not DB_PATH.exists():
        print(f"[🛑 ERROR] Database ledger missing at {DB_PATH}. Run a backtest first.")
        return
        
    print("\n=====================================================================")
    print("        APEX QUANT SYSTEMS — NEGATIVE-SPACE TELEMETRY REPORT        ")
    print("=====================================================================")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verify the target table exists inside the discovered storage file
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='denied_signals';")
        if not cursor.fetchone():
            print("[⚠️ EMPTY STATUS] The ledger exists, but no denial entries have been saved yet.")
            return

        # Metric Extraction 1: Total Rejections By Asset Ticker
        print("\n[📊 ASSET REJECTION MATRIX]")
        cursor.execute("""
            SELECT symbol, COUNT(*), AVG(score), AVG(displacement) 
            FROM denied_signals 
            GROUP BY symbol
        """)
        print(f"{'Asset':<12} | {'Blocks':<10} | {'Avg Conviction':<16} | {'Avg Displacement'}")
        print("-" * 65)
        for row in cursor.fetchall():
            print(f"{row[0]:<12} | {row[1]:<10} | {row[2]:<16.4f} | {row[3]:.4f}")
            
        # Metric Extraction 2: Rejections Sorted By Market Regime
        print("\n[🧠 REGIME FILTER EFFICIENCY]")
        cursor.execute("""
            SELECT regime, COUNT(*), reason 
            FROM denied_signals 
            GROUP BY regime, reason
        """)
        print(f"{'Market Regime':<15} | {'Blocks':<10} | {'Primary Gate Failure Cause'}")
        print("-" * 65)
        for row in cursor.fetchall():
            print(f"{row[0]:<15} | {row[1]:<10} | {row[2]}")
            
        # Metric Extraction 3: High-Value Edge Protection Summary
        cursor.execute("SELECT COUNT(*) FROM denied_signals")
        total_blocks = cursor.fetchone()[0]
        print("\n---------------------------------------------------------------------")
        print(f"[✓ VERDICT] System successfully suppressed {total_blocks} toxic entries across the timeline.")
        print("=====================================================================\n")

    except sqlite3.OperationalError as e:
        print(f"[🛑 DATABASE ACCESS ERROR] {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    harvest_negative_space_metrics()
