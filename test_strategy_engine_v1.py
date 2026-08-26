# filename: test_strategy_engine_v1.py
import unittest
from datetime import datetime
from core.interfaces.contracts import TimeframeState, MarketIntelligenceSnapshot, MarketTrend, MarketStructure, MarketPhase, SignalDirection
from strategy.strategy_engine_v1 import ApexStrategyEngineV1

class TestStrategyEngineV1(unittest.TestCase):
    def setUp(self):
        self.strategy = ApexStrategyEngineV1(min_confidence_threshold=50.0)
        
        # Seed standardized mock timeframe elements matching the contract format
        self.base_state = lambda trend, struct, phase, keyzones=None, liq=None: TimeframeState(
            trend=trend, structure=struct, phase=phase,
            keyzones=keyzones or [], liquidity_pools=liq or [],
            confidence=90.0, strength=50.0, invalidated=False, quality_score=5.0,
            timestamp=datetime.utcnow()
        )

    def test_perfect_bullish_alignment_matrix(self):
        # Setup: A = Bullish Trend, B = In corrective Pullback state, C = Triggers structural break high
        snapshot = MarketIntelligenceSnapshot(
            symbol="BTCUSDT",
            timeframe_a=self.base_state(MarketTrend.BULLISH, MarketStructure.CONSOLIDATION, MarketPhase.EXPANSION, liq=[72000.0]),
            timeframe_b=self.base_state(MarketTrend.BEARISH, MarketStructure.CONSOLIDATION, MarketPhase.PULLBACK),
            timeframe_c=self.base_state(MarketTrend.BULLISH, MarketStructure.BOS_HIGH, MarketPhase.EXPANSION, keyzones=[64000.0])
        )

        decision = self.strategy.evaluate_alignment(snapshot)
        
        self.assertEqual(decision.direction, SignalDirection.BUY)
        self.assertTrue(decision.timeframe_b_aligned)
        self.assertTrue(decision.timeframe_c_triggered)
        self.assertEqual(decision.structural_anchor_levels["ltf_invalidation"], 64000.0)
        self.assertEqual(decision.structural_anchor_levels["htf_target"], 72000.0)

    def test_short_circuit_on_neutral_macro_bias(self):
        # Setup: Timeframe A defaults to Neutral, forcing an immediate short-circuit to WAIT
        snapshot = MarketIntelligenceSnapshot(
            symbol="ETHUSDT",
            timeframe_a=self.base_state(MarketTrend.NEUTRAL, MarketStructure.CONSOLIDATION, MarketPhase.ACCUMULATION),
            timeframe_b=self.base_state(MarketTrend.BULLISH, MarketStructure.BOS_HIGH, MarketPhase.EXPANSION),
            timeframe_c=self.base_state(MarketTrend.BULLISH, MarketStructure.BOS_HIGH, MarketPhase.EXPANSION)
        )

        decision = self.strategy.evaluate_alignment(snapshot)
        self.assertEqual(decision.direction, SignalDirection.WAIT)
        self.assertFalse(decision.timeframe_b_aligned)

if __name__ == "__main__":
    unittest.main()
