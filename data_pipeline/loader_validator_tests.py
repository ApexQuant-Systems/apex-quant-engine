# filename: data_pipeline/loader_validator_tests.py
import unittest
import os
from data_pipeline.data_validator import ApexDataValidator
from data_pipeline.historical_loader import ApexHistoricalLoader
from data_pipeline.binance_adapter import BinanceExchangeAdapter
from core.database.vault import ApexStorageVault

class MockFaultyAdapter:
    """Simulates highly corrupted market anomalies for edge-case defense validation."""
    def fetch_historical_candles(self, symbol: str, interval: str, limit: int):
        return [
            [1700000000000, "50000", "45000", "60000", "55000", "100"], # Anomaly: Low > High
            [1700000060000, "55000", "56000", "54000", "55500", "-5"],  # Anomaly: Negative Volume
        ]

class TestLoaderValidatorIntegration(unittest.TestCase):
    def setUp(self):
        self.validator = ApexDataValidator()
        self.vault = ApexStorageVault() # Ensures standard db tables exist safely

    def test_module_1_6_geometry_checks(self):
        # Perfect block structure configuration setup
        clean_candle = [1700000000000, 100.0, 105.0, 95.0, 102.0, 500.0]
        passed, msg = self.validator.verify_candle_geometry(clean_candle)
        self.assertTrue(passed)

        # Testing inverted space boundaries
        bad_candle = [1700000000000, 100.0, 90.0, 110.0, 102.0, 500.0]
        passed, msg = self.validator.verify_candle_geometry(bad_candle)
        self.assertFalse(passed)
        self.assertEqual(msg, "ERR_GEOMETRIC_INVERSION_LOW_ABOVE_HIGH")

    def test_module_1_4_anomaly_interception_rate(self):
        mock_adapter = MockFaultyAdapter()
        loader = ApexHistoricalLoader(mock_adapter, self.validator)
        
        # Intercepts corruption rows locally without appending entries to database lines
        written_rows = loader.download_and_sync("BTCUSDT", "15m", limit=2)
        self.assertEqual(written_rows, 0)

    def test_live_isolated_pipeline_handshake(self):
        live_adapter = BinanceExchangeAdapter()
        loader = ApexHistoricalLoader(live_adapter, self.validator)
        
        # Pull down an active production snapshot batch
        committed = loader.download_and_sync("SOLUSDT", "1h", limit=5)
        # Should cleanly download or recognize entries that already occupy storage keys
        self.assertTrue(committed >= 0)

if __name__ == "__main__":
    unittest.main()
