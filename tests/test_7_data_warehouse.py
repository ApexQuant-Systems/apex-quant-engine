# filename: tests/test_7_data_warehouse.py
import unittest
import sys
import os
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_engine.data_ingestor import DataIngestor
from config.global_config import GLOBAL_CONFIG

class TestDataWarehouse(unittest.TestCase):
    def test_ingestion(self):
        ingestor = DataIngestor()
        records = ingestor.fetch_ohlcv("BTCUSDT", "1h", limit=100)
        ingestor.store_data(records)
        
        conn = sqlite3.connect(GLOBAL_CONFIG.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM market_data WHERE symbol='BTCUSDT'")
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertGreaterEqual(count, 100)
        print(f"\n[DIAGNOSTIC] Data Warehouse Verified: {count} rows in storage.")

if __name__ == '__main__':
    unittest.main()
