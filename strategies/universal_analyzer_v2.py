import os
import sys
import time

class ApexStructuralAnalyzer:
    """
    🛰️ APEX UNIVERSAL ENGINE: VERSION 1.3.0
    Houses the complete 4-Set Multi-Timeframe Structural Matrix.
    Applies market-agnostic geometry rules across Crypto, Forex, Indices, and Commodities.
    """
    def __init__(self):
        self.version = "1.3.0"
        
        # Formalizing your 4 foundational multi-timeframe horizons
        self.strategy_sets = {
            1: {"name": "SET_1_MACRO_TREND", "htf": "1M", "mtf": "1W", "ltf": "1D"},
            2: {"name": "SET_2_SWING_FRAME", "htf": "1W", "mtf": "1D", "ltf": "4H"},
            3: {"name": "SET_3_INTRADAY_TREND", "htf": "1D", "mtf": "4H", "ltf": "1H"},
            4: {"name": "SET_4_INTRADAY_SCALP", "htf": "4H", "mtf": "1H", "ltf": "15M"}
        }
        print(f"  ├── [UNIVERSAL ENGINE] Matrix successfully latched for ALL 4 STRATEGY SETS.")

    def classify_asset_group(self, symbol: str) -> str:
        """Determines financial categories with corrected precedence sequencing."""
        sym = symbol.upper()
        # 1. Check commodities first to catch metals/oils paired with USD (e.g., XAUUSD)
        if any(commodity in sym for commodity in ["XAU", "WTI", "BRENT", "OIL"]):
            return "COMMODITIES"
        # 2. Check stock index patterns
        if any(index in sym for index in ["100", "30", "500", "GER", "NAS"]):
            return "INDICES"
        # 3. Fall back to Forex if it contains traditional currency strings
        if "USD" in sym and not any(crypto in sym for crypto in ["BTC", "ETH", "SOL"]):
            return "FOREX"
        return "CRYPTO"

    def evaluate_set_geometry(self, set_id: int, symbol: str, entry: float, htf_tp: float, ltf_sl: float, mtf_trend: str) -> dict:
        """
        Evaluates a specified strategy set ID against dynamic zone geometry.
        Enforces your structural rules: HTF Target = TP | LTF Zone = SL | MTF = Trailing
        """
        if set_id not in self.strategy_sets:
            return {"error": f"Strategy SET {set_id} not registered in core matrix."}

        set_meta = self.strategy_sets[set_id]
        asset_class = self.classify_asset_group(symbol)
        
        # Calculate pure spatial risk/reward distances
        risk_distance = abs(entry - ltf_sl)
        reward_distance = abs(htf_tp - entry)
        raw_rr = reward_distance / risk_distance if risk_distance > 0 else 0.0
        
        # Enforce minimum selection constraint parameter
        geometry_gate = "PASS" if raw_rr >= 4.0 else "FAIL"
        
        final_signal = "NO_TRADE"
        if geometry_gate == "PASS":
            if mtf_trend.upper() == "BULLISH" and htf_tp > entry:
                final_signal = "BUY"
            elif mtf_trend.upper() == "BEARISH" and htf_tp < entry:
                final_signal = "SELL"

        return {
            "set_id": set_id,
            "set_name": set_meta["name"],
            "timeframe_map": f"HTF:{set_meta['htf']} -> MTF:{set_meta['mtf']} -> LTF:{set_meta['ltf']}",
            "symbol": symbol.upper(),
            "asset_class": asset_class,
            "entry_price": entry,
            "structural_sl": ltf_sl,
            "structural_tp": htf_tp,
            "calculated_rr": round(raw_rr, 2),
            "geometry_gate": geometry_gate,
            "mtf_trailing_context": f"TRAILING_{mtf_trend.upper()}",
            "final_signal": final_signal
        }
