# filename: strategy/strategy_engine_v1.py
import logging
from datetime import datetime
from core.interfaces.contracts import (
    MarketIntelligenceSnapshot, 
    StrategyDecision, 
    SignalDirection, 
    MarketTrend, 
    MarketPhase,
    MarketStructure
)

class ApexStrategyEngineV1:
    """
    Module 2: Strategy Engine (Version 1.0.0).
    Evaluates top-down structural alignment across abstract timeframes.
    Completely decoupled from raw candles and implementation mathematics.
    """
    def __init__(self, min_confidence_threshold: float = 50.0):
        self.min_confidence_threshold = min_confidence_threshold
        self.logger = logging.getLogger("ApexStrategyEngineV1")

    def evaluate_alignment(self, snapshot: MarketIntelligenceSnapshot) -> StrategyDecision:
        """
        Executes sequential alignment filters:
        Timeframe A (Bias) -> Timeframe B (Setup Zone) -> Timeframe C (Precision Trigger)
        """
        symbol = snapshot.symbol
        tf_a = snapshot.timeframe_a
        tf_b = snapshot.timeframe_b
        tf_c = snapshot.timeframe_c

        # Gate 0: Ensure database data tracking confidence thresholds are respected
        if tf_a.confidence < self.min_confidence_threshold:
            return self._generate_wait_decision(symbol, tf_a.trend, "LOW_HTF_CONFIDENCE")

        # Gate 1: Timeframe A - Establish Structural Reality/Bias Vector
        if tf_a.trend == MarketTrend.NEUTRAL:
            return self._generate_wait_decision(symbol, tf_a.trend, "TIMEFRAME_A_NEUTRAL")
        
        primary_bias = tf_a.trend
        
        # Gate 2: Timeframe B - Validate Value Area Setup Alignment
        # Fluid mathematical logic: Aligned if it's returning matching bias OR in a valid corrective pullback phase
        tf_b_aligned = (tf_b.trend == primary_bias) or (tf_b.phase == MarketPhase.PULLBACK)
        if not tf_b_aligned:
            return self._generate_wait_decision(symbol, primary_bias, "TIMEFRAME_B_MISALIGNED")

        # Gate 3: Timeframe C - Confirm Precision Entry Trigger
        # Fluid trigger logic: Confirmed if a structural breakout step occurs in the direction of our primary bias
        tf_c_triggered = False
        if primary_bias == MarketTrend.BULLISH and tf_c.structure in [MarketStructure.BOS_HIGH, MarketStructure.CHOCH_HIGH]:
            tf_c_triggered = True
        elif primary_bias == MarketTrend.BEARISH and tf_c.structure in [MarketStructure.BOS_LOW, MarketStructure.CHOCH_LOW]:
            tf_c_triggered = True

        if not tf_c_triggered:
            return self._generate_wait_decision(
                symbol, primary_bias, "TIMEFRAME_C_NO_TRIGGER", tf_b_aligned=True
            )

        # Step 4: Compute Convergence Score Matrix and anchor level geometries
        composite_score = (tf_a.confidence + tf_b.confidence + tf_c.confidence) / 3.0
        direction = SignalDirection.BUY if primary_bias == MarketTrend.BULLISH else SignalDirection.SELL

        # Abstract anchor dictionary mapping used for subsequent trade geometry tracking
        anchor_levels = {}
        if tf_c.keyzones:
            anchor_levels["ltf_invalidation"] = tf_c.keyzones[0]
        if tf_a.liquidity_pools:
            anchor_levels["htf_target"] = tf_a.liquidity_pools[0]

        return StrategyDecision(
            symbol=symbol,
            direction=direction,
            timeframe_a_bias=primary_bias,
            timeframe_b_aligned=True,
            timeframe_c_triggered=True,
            convergence_score=composite_score,
            structural_anchor_levels=anchor_levels,
            timestamp=datetime.utcnow()
        )

    def _generate_wait_decision(self, symbol: str, bias: MarketTrend, reason: str, tf_b_aligned: bool = False) -> StrategyDecision:
        """Helper method to construct standardized short-circuit entries cleanly."""
        return StrategyDecision(
            symbol=symbol,
            direction=SignalDirection.WAIT,
            timeframe_a_bias=bias,
            timeframe_b_aligned=tf_b_aligned,
            timeframe_c_triggered=False,
            convergence_score=0.0,
            structural_anchor_levels={},
            timestamp=datetime.utcnow()
        )
