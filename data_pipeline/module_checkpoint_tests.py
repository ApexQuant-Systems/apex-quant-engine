# filename: data_pipeline/module_checkpoint_tests.py
import unittest
from data_pipeline.asset_manager import ApexAssetManager
from data_pipeline.timeframe_manager import ApexTimeframeManager
from data_pipeline.binance_adapter import BinanceExchangeAdapter

class TestApexDataModules(unittest.TestCase):
    def setUp(self):
        self.asset_mgr = ApexAssetManager()
        self.tf_mgr = ApexTimeframeManager()
        self.adapter = BinanceExchangeAdapter()

    def test_module_1_1_asset_guards(self):
        self.assertTrue(self.asset_mgr.is_allowed("BTCUSDT"))
        self.assertFalse(self.asset_mgr.is_allowed("EURUSD"))  # Confirms Forex block is active
        self.assertFalse(self.asset_mgr.is_allowed("XAUUSD"))  # Confirms Gold block is active

    def test_module_1_2_timeframe_normalization(self):
        self.assertEqual(self.tf_mgr.normalize_interval("15M"), "15m")
        self.assertEqual(self.tf_mgr.normalize_interval("4H"), "4h")
        with self.assertRaises(ValueError):
            self.tf_mgr.normalize_interval("3H") # Confirms invalid intervals break cleanly

    def test_module_1_3_adapter_isolation(self):
        # Queries live sandbox data with standardized parameters
        result = self.adapter.fetch_historical_candles("BTCUSDT", "1d", limit=5)
        if result:
            self.assertTrue(len(result) <= 5)
            # Confirm data mapping length layout: [Time, O, H, L, C, V]
            self.assertEqual(len(result[0]), 6)

if __name__ == "__main__":
    unittest.main()
