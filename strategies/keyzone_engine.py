import os
import sys

class ApexKeyzoneEngine:
    """
    🛰️ APEX OPERATING SYSTEM: PHASE 2.4 KEYZONE ENGINE
    Decoupled language module tracking institutional supply/demand footprints:
    Fair Value Gaps (FVG) and high-volume Order Blocks (OB).
    """
    def __init__(self):
        self.version = "2.0.0"

    def scan_institutional_keyzones(self, open_arr: list, high_arr: list, low_arr: list, close_arr: list, confirmed_bos: str) -> dict:
        """
        Scans closed price arrays row-by-row to map out active imbalance gaps and order footprints.
        """
        total_bars = len(close_arr)
        if total_bars < 4:
            return {"active_fvg": None, "active_ob_zone": None}

        active_fvg = None
        active_ob_zone = None

        # 1. 📐 FAIR VALUE GAP (FVG) DETECTION LOOP
        # Inspects the last three closed candles for structural inefficiency
        # Bullish FVG: Space between Candle -3 High and Candle -1 Low
        if high_arr[-3] < low_arr[-1]:
            active_fvg = {
                "type": "BULLISH_FVG",
                "ceiling": low_arr[-1],
                "floor": high_arr[-3]
            }
        # Bearish FVG: Space between Candle -3 Low and Candle -1 High
        elif low_arr[-3] > high_arr[-1]:
            active_fvg = {
                "type": "BEARISH_FVG",
                "ceiling": low_arr[-3],
                "floor": high_arr[-1]
            }

        # 2. 📐 INSTITUTIONAL ORDER BLOCK (OB) FOOTPRINT ISOLATION
        # If the structure engine flags a confirmed breakout (BOS), we look backward
        # to locate the origin candle that initiated the displacement move.
        if confirmed_bos == "BOS_BULLISH":
            # Search backward for the last bearish candle before the expansion
            for idx in range(total_bars - 2, 0, -1):
                if close_arr[idx] < open_arr[idx]:
                    active_ob_zone = {
                        "type": "BULLISH_OB",
                        "top": high_arr[idx],
                        "bottom": low_arr[idx]
                    }
                    break
        elif confirmed_bos == "BOS_BEARISH":
            # Search backward for the last bullish candle before the breakdown
            for idx in range(total_bars - 2, 0, -1):
                if close_arr[idx] > open_arr[idx]:
                    active_ob_zone = {
                        "type": "BEARISH_OB",
                        "top": high_arr[idx],
                        "bottom": low_arr[idx]
                    }
                    break

        return {
            "active_fvg": active_fvg,
            "active_ob_zone": active_ob_zone
        }

if __name__ == "__main__":
    engine = ApexKeyzoneEngine()
    print("Core institutional keyzone and imbalance engine successfully compiled.")
