# filename: test_market_intelligence_v1.py
import unittest
from market_language.market_intelligence_v1 import ApexMarketIntelligenceV1
from core.interfaces.contracts import MarketTrend, MarketStructure, MarketPhase

class TestMarketIntelligenceEngineV1(unittest.TestCase):
    def setUp(self):
        self.engine = ApexMarketIntelligenceV1(baseline_period=5, structure_window=2)
        
        # Build an uncorrupted chronological data series simulating a structural break out upside
        self.simulated_market_data = [
            {"close": 100.0, "high": 102.0, "low": 98.0},
            {"close": 101.0, "high": 103.0, "low": 99.0},
            {"close": 102.0, "high": 104.0, "low": 101.0}, # Historic High point
            {"close": 100.0, "high": 101.5, "low": 99.5},
            {"close": 106.0, "high": 107.0, "low": 103.0}  # Volatile breakout candle body close past 104.0
        ]

    def test_incremental_state_parsing(self):
        state = self.engine.process_candle_matrix(self.simulated_market_data)
        
        # Assert type output compliance against core interfaces
        self.assertIsInstance(state.trend, MarketTrend)
        self.assertIsInstance(state.structure, MarketStructure)
        self.assertIsInstance(state.phase, MarketPhase)
        
        # Verify lookahead-free breakout mapping (Close 106.0 > Historic High 104.0)
        self.assertEqual(state.trend, MarketTrend.BULLISH)
        self.assertEqual(state.structure, MarketStructure.BOS_HIGH)
        self.assertEqual(state.phase, MarketPhase.EXPANSION)
        
        # Verify placeholder encapsulation safety
        self.assertEqual(state.keyzones, [])
        self.assertEqual(state.liquidity_pools, [])
        self.assertTrue(state.strength > 0.0)

    def test_fallback_stability_on_empty_arrays(self):
        fallback = self.engine.process_candle_matrix([])
        self.assertEqual(fallback.trend, MarketTrend.NEUTRAL)
        self.assertEqual(fallback.confidence, 0.0)

if __name__ == "__main__":
    unittest.main()
