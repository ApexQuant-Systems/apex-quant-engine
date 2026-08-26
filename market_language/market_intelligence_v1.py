# filename: market_language/market_intelligence_v1.py
import logging
from datetime import datetime
from typing import List, Dict, Any
from core.interfaces.contracts import TimeframeState, MarketTrend, MarketStructure, MarketPhase

class ApexMarketIntelligenceV1:
    """
    Module 1: Market Language Engine (Version 1.0.0).
    Implements incremental structural parsing with absolute lookahead protection.
    Downstream strategy engines consume this output instead of raw price fields.
    """
    def __init__(self, baseline_period: int = 20, structure_window: int = 5):
        self.baseline_period = baseline_period
        self.structure_window = structure_window
        self.logger = logging.getLogger("ApexMarketIntelligenceV1")

    def _calculate_sma(self, values: List[float], period: int) -> float:
        if len(values) < period:
            return sum(values) / len(values) if values else 0.0
        return sum(values[-period:]) / period

    def process_candle_matrix(self, candles: List[Dict[str, Any]]) -> TimeframeState:
        """
        Translates raw lookback price rows into a frozen, unified state contract.
        Guarantees zero repainting or lookahead errors by processing up to index t only.
        """
        if len(candles) < max(self.baseline_period, self.structure_window * 2 + 1):
            return self.generate_fallback_state()

        # Extract numerical vector dimensions cleanly
        closes = [float(c["close"]) for c in candles]
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        
        current_close = closes[-1]
        current_high = highs[-1]
        current_low = lows[-1]

        # 1. EVALUATE TREND VECTOR (Fluid internal math logic)
        baseline = self._calculate_sma(closes, self.baseline_period)
        if current_close > baseline:
            trend_state = MarketTrend.BULLISH
        elif current_close < baseline:
            trend_state = MarketTrend.BEARISH
        else:
            trend_state = MarketTrend.NEUTRAL

        # 2. EVALUATE STRUCTURE STATES (Lookahead-Protected Pivot Checks)
        # Find the most recent confirmed swing extreme inside historical data boundaries
        last_high_extreme = max(highs[-self.baseline_period:-self.structure_window])
        last_low_extreme = min(lows[-self.baseline_period:-self.structure_window])

        if current_close > last_high_extreme:
            structure_state = MarketStructure.BOS_HIGH
            phase_state = MarketPhase.EXPANSION
        elif current_close < last_low_extreme:
            structure_state = MarketStructure.BOS_LOW
            phase_state = MarketPhase.EXPANSION
        else:
            structure_state = MarketStructure.CONSOLIDATION
            phase_state = MarketPhase.PULLBACK

        # 3. COMPUTE NORMALIZED METRICS
        # Strength maps the proportional distance away from our core baseline anchor
        strength_metric = abs(current_close - baseline) / baseline * 100.0 if baseline > 0 else 0.0
        
        # Confidence score measures sample size depth up to the current evaluation sequence
        confidence_metric = min(100.0, float(len(candles) / 100.0) * 100.0)

        # Return explicit structural contracts matching the immutable specification
        return TimeframeState(
            trend=trend_state,
            structure=structure_state,
            phase=phase_state,
            keyzones=[],            # V1 Placeholder: To be implemented via V2 Order Block matchers
            liquidity_pools=[],     # V1 Placeholder: To be implemented via V2 Wick Sweeper logic
            confidence=confidence_metric,
            strength=strength_metric,
            invalidated=False,
            quality_score=5.0,      # Fixed baseline score for initial stable release
            timestamp=datetime.utcnow()
        )

    def generate_fallback_state(self) -> TimeframeState:
        """Returns a safe, neutral fallback state if sample boundaries are insufficient."""
        return TimeframeState(
            trend=MarketTrend.NEUTRAL,
            structure=MarketStructure.CONSOLIDATION,
            phase=MarketPhase.ACCUMULATION,
            keyzones=[],
            liquidity_pools=[],
            confidence=0.0,
            strength=0.0,
            invalidated=False,
            quality_score=0.0,
            timestamp=datetime.utcnow()
        )
