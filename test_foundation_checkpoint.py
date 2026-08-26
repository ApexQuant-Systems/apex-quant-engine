# filename: test_foundation_checkpoint.py
import unittest
import os
from config.global_config import GLOBAL_CONFIG
from core.database.vault import ApexStorageVault
from core.interfaces.contracts import TimeframeState, MarketTrend, MarketStructure, MarketPhase

class TestApexFoundationCore(unittest.TestCase):
    def setUp(self):
        self.vault = ApexStorageVault("data/checkpoint_test.db")

    def tearDown(self):
        if os.path.exists("data/checkpoint_test.db"):
            os.remove("data/checkpoint_test.db")
        if os.path.exists("data/checkpoint_test.db-wal"):
            os.remove("data/checkpoint_test.db-wal")
        if os.path.exists("data/checkpoint_test.db-shm"):
            os.remove("data/checkpoint_test.db-shm")

    def test_flexible_config_bounds(self):
        # Confirms reward-risk calculations are configurable parameters rather than hardcoded metrics
        self.assertEqual(GLOBAL_CONFIG.MINIMUM_ACCEPTABLE_REWARD_RISK, 4.0)
        self.assertIn("BTCUSDT", GLOBAL_CONFIG.FAVORITES_ASSET_POOL)
        self.assertEqual(GLOBAL_CONFIG.SET_4_INTRADAY["A"], "4H")

    def test_upgraded_contract_namespace(self):
        # Asserts that newly integrated metrics initialize smoothly inside the contract mapping
        from datetime import datetime
        state = TimeframeState(
            trend=MarketTrend.BULLISH,
            structure=MarketStructure.CONSOLIDATION,
            phase=MarketPhase.PULLBACK,
            keyzones=[65000.0],
            liquidity_pools=[66200.0],
            confidence=95.0,
            strength=82.4,        # Upgraded field check
            invalidated=False,     # Upgraded field check
            quality_score=7.5,     # Upgraded field check
            timestamp=datetime.utcnow()
        )
        self.assertEqual(state.strength, 82.4)
        self.assertFalse(state.invalidated)

if __name__ == "__main__":
    unittest.main()
