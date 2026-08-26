import os
import sqlite3

def provision_institutional_tables():
    db_path = "data/forward_testing_vault.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    print("=====================================================================")
    print(" 🛰️ APEX STORAGE LAYER: PROVISIONING MULTI-TABLE SYSTEM SCHEMAS")
    print("=====================================================================")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable Write-Ahead Logging (WAL) for high-performance concurrent reading/writing
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    tables = {
        "market_ticks": """
            CREATE TABLE IF NOT EXISTS market_ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume REAL NOT NULL
            );
        """,
        "candles": """
            CREATE TABLE IF NOT EXISTS candles (
                timestamp INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL
            );
        """,
        "orders": """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                strategy_set TEXT NOT NULL,
                direction TEXT NOT NULL,
                price REAL NOT NULL,
                status TEXT NOT NULL
            );
        """,
        "positions": """
            CREATE TABLE IF NOT EXISTS positions (
                symbol TEXT PRIMARY KEY,
                entry_time INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                sl_price REAL NOT NULL,
                tp_price REAL NOT NULL,
                current_exposure REAL NOT NULL,
                status TEXT NOT NULL
            );
        """,
        "system_events": """
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                module_source TEXT NOT NULL,
                message TEXT NOT NULL
            );
        """
    }
    
    for name, schema in tables.items():
        try:
            cursor.execute(schema)
            print(f"  ├── [SCHEMA COMPLIANT] Table initialized: {name}")
        except Exception as e:
            print(f"  ❌ [SCHEMA ERROR] Failed to provision {name}: {e}")
            
    conn.commit()
    conn.close()
    print("=====================================================================")
    print("🏁 PRIORITY 2 INITIALIZATION COMPLETE: PLATFORM DATA VAULT IS READY")

if __name__ == "__main__":
    provision_institutional_tables()
