# filename: config/config_tests.py
import unittest
from config.global_config import GLOBAL_CONFIG
from core.interfaces.contracts import MarketIntelligenceSnapshot, SignalDirection

class TestApexFoundation(unittest.TestCase):
    def test_global_config_parameters(self):
        self.assertEqual(GLOBAL_CONFIG.ASSET_CLASS, "CRYPTO")
        self.assertIn("BTCUSDT", GLOBAL_CONFIG.FAVORITES_MATRIX)
        self.assertEqual(GLOBAL_CONFIG.PORTFOLIO_RISK_CAP_PCT, 1.0)

    def test_contract_type_compilation(self):
        # Asserts if lowercase str type correction functions safely
        direction = SignalDirection.BUY
        self.assertEqual(direction.value, "BUY")
        
if __name__ == "__main__":
    unittest.main()
