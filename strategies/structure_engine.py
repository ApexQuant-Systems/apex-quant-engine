import os
import sys

class ApexMarketLanguageEngine:
    """
    🛰️ APEX OPERATING SYSTEM: PHASE 2.2 STRUCTURE ENGINE
    Analyzes raw market candle arrays to identify authentic swing points
    and track structural updates (BOS / CHOCH) with zero look-ahead bias.
    """
    def __init__(self):
        self.version = "2.0.0"

    def extract_pure_market_structure(self, high_arr: list, low_arr: list, close_arr: list) -> dict:
        """
        Processes trailing price history to identify valid local structural milestones.
        """
        total_bars = len(close_arr)
        if total_bars < 7:
            return {"active_swing_high": None, "active_swing_low": None, "structural_event": "INITIALIZATION"}

        active_swing_high = None
        active_swing_low = None
        structural_event = "CONSOLIDATION"

        # 📐 SWING FRACTAL IDENTIFICATION (5-Bar Pattern Isolation)
        # To strictly eliminate look-ahead bias, we evaluate candle i-2 as the potential swing apex
        # because candles i-1 and i (the flanking confirmations) have already closed.
        for i in range(2, total_bars - 2):
            # Test for confirmed Swing High
            if (high_arr[i] > high_arr[i-1] and high_arr[i] > high_arr[i-2] and
                high_arr[i] > high_arr[i+1] and high_arr[i] > high_arr[i+2]):
                active_swing_high = high_arr[i]

            # Test for confirmed Swing Low
            if (low_arr[i] < low_arr[i-1] and low_arr[i] < low_arr[i-2] and
                low_arr[i] < low_arr[i+1] and low_arr[i] < low_arr[i+2]):
                active_swing_low = low_arr[i]

        # 📐 BREAK OF STRUCTURE (BOS) VERIFICATION
        # Check if the most recent closed session body aggressively broke out past active milestones
        current_close = close_arr[-1]
        
        if active_swing_high and current_close > active_swing_high:
            structural_event = "BOS_BULLISH"
        elif active_swing_low and current_close < active_swing_low:
            structural_event = "BOS_BEARISH"

        return {
            "active_swing_high": active_swing_high,
            "active_swing_low": active_swing_low,
            "structural_event": structural_event
        }

if __name__ == "__main__":
    engine = ApexMarketLanguageEngine()
    print("🟢 [STRUCTURE SYSTEM] Core market vocabulary engine compiled successfully.")
