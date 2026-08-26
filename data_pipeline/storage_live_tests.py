# filename: data_pipeline/storage_live_tests.py
import unittest
import asyncio
import sqlite3
from data_pipeline.storage_manager import ApexStorageManager
from data_pipeline.live_feed import ApexLiveFeedEngine
from config.global_config import GLOBAL_CONFIG

class TestStorageAndLiveFeed(unittest.TestCase):
    def setUp(self):
        self.storage_mgr = ApexStorageManager()
        self.received_ticks = []

        # Ensure dummy entry exists within standard database lines for query isolation testing
        conn = sqlite3.connect(GLOBAL_CONFIG.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES ('BTCUSDT', '15m', '2026-01-01 00:00:00', 60000.0, 61000.0, 59000.0, 60500.0, 10.0)
        """)
        conn.commit()
        conn.close()

    def _mock_callback(self, tick: dict):
        self.received_ticks.append(tick)

    def test_module_1_7_storage_abstraction(self):
        records = self.storage_mgr.get_historical_candles("BTCUSDT", "15m", limit=1)
        self.assertTrue(len(records) >= 1)
        # Verify columns are parsed into direct dictionary keys
        self.assertIn("close", records[0])
        self.assertEqual(records[0]["symbol"], "BTCUSDT")

    def test_module_1_5_async_tick_distribution(self):
        engine = ApexLiveFeedEngine(target_symbols=["BTCUSDT"])
        engine.register_subscriber(self._mock_callback)
        
        # Run async loop simulation harness cleanly
        asyncio.run(engine.start_simulated_stream(test_cycles=3))
        
        self.assertEqual(len(self.received_ticks), 3)
        self.assertEqual(self.received_ticks[0]["symbol"], "BTCUSDT")

if __name__ == "__main__":
    unittest.main()
