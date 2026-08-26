import pandas as pd
import numpy as np
from core.interfaces.contracts import MarketState

class IntelligenceEngine:
    def __init__(self, lookback: int = 5, atr_mult: float = 0.02):
        self.lookback = lookback
        self.atr_mult = atr_mult

    def calculate_intelligence(self, df: pd.DataFrame) -> MarketState:
        # Identify Fractals (Pivots) - Only consider candles where the high/low is the highest/lowest in the window
        # This prevents triggering on every candle
        df['is_pivot_high'] = df['high'] == df['high'].rolling(self.lookback * 2 + 1, center=True).max()
        df['is_pivot_low'] = df['low'] == df['low'].rolling(self.lookback * 2 + 1, center=True).min()
        
        # Get the most recent pivot levels
        recent_pivots = df[df['is_pivot_high'] | df['is_pivot_low']]
        if recent_pivots.empty:
            return MarketState("BTCUSDT", "1h", "NEUTRAL", "HH_HL", "EXPANSION", ["OB_1"], [], 85.0, 90.0, False, float(df.index[-1].timestamp()))

        last_pivot_high = recent_pivots[recent_pivots['is_pivot_high']]['high'].iloc[-1] if not recent_pivots[recent_pivots['is_pivot_high']].empty else 0
        last_pivot_low = recent_pivots[recent_pivots['is_pivot_low']]['low'].iloc[-1] if not recent_pivots[recent_pivots['is_pivot_low']].empty else 0
        
        curr_high = df['high'].iloc[-1]
        curr_low = df['low'].iloc[-1]
        curr_close = df['close'].iloc[-1]
        
        liquidity = []
        # Only trigger sweep if we break a *pivot* level, not just the previous candle
        if last_pivot_high > 0 and curr_high > last_pivot_high and curr_close < last_pivot_high:
            liquidity.append("EQH_SWEEP")
        if last_pivot_low > 0 and curr_low < last_pivot_low and curr_close > last_pivot_low:
            liquidity.append("EQL_SWEEP")

        return MarketState(
            symbol="BTCUSDT",
            timeframe="1h",
            trend="NEUTRAL",
            structure="HH_HL",
            phase="EXPANSION",
            keyzones=["OB_1"],
            liquidity=liquidity,
            strength=85.0,
            confidence=90.0,
            invalidated=False,
            timestamp=float(df.index[-1].timestamp())
        )
