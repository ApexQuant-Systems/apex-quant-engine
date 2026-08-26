import os
import sys
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.project_config import ApexGlobalConfiguration
from utils.system_logger import ApexSystemLogger

log = ApexSystemLogger.get_initialized_logger("DATABASE_VAULT")

class ApexDatabaseWarehouse:
    """
    🛰️ APEX OPERATING SYSTEM: STRUCTURAL DATA WAREHOUSE
    Manages schemas, index allocation loops, and database connections.
    """
    def __init__(self):
        self.db_path = ApexGlobalConfiguration.DATABASE_PATH
        self.initialize_warehouse()

    def initialize_warehouse(self):
        """Creates the relational multi-timeframe storage engine schema structures."""
        log.info(f"Connecting to database repository target: {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Deploy clear, partitioned market bar tracking fields
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS multi_timeframe_market_bars (
                bar_id TEXT PRIMARY KEY,
                timestamp INTEGER,
                symbol TEXT,
                asset_class TEXT,
                interval TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL
            )
        """)
        
        # Optimize queries by indexing symbol and interval combinations
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sym_int ON multi_timeframe_market_bars (symbol, interval)")
        conn.commit()
        conn.close()
        log.info("🟢 [VAULT INITIALIZED] Multi-resolution relational schema successfully latched.")

if __name__ == "__main__":
    warehouse = ApexDatabaseWarehouse()
