import sqlite3
import os

DB_PATH = "./data/forward_testing_vault.db"

def initialize_market_state_table():
    """Creates a dedicated live telemetry table for the Markets scanner page."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create a table to track current multi-timeframe conditions for scanned assets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_telemetry (
            asset TEXT PRIMARY KEY,
            asset_class TEXT,
            htf_bias TEXT,
            mtf_trend TEXT,
            ltf_trigger TEXT,
            last_price REAL,
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("💾 Market telemetry state database table initialized successfully.")

if __name__ == "__main__":
    initialize_market_state_table()
