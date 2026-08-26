import os
import sys

class ApexHierarchicalStateEngine:
    """
    🛰️ APEX UNIVERSAL ENGINE: VERSION 1.9.0 (WINDOW MEMORY)
    Extracts true HTF -> MTF -> LTF structural state progressions by analyzing
    rolling historical window price paths instead of single isolated candles.
    """
    def __init__(self):
        self.version = "1.9.0"
        # Map out explicit lookback window properties per strategy horizon set
        self.window_matrix = {
            1: {"name": "SET_1_MACRO_TREND", "htf_len": 40, "mtf_len": 10},
            2: {"name": "SET_2_SWING_FRAME", "htf_len": 20, "mtf_len": 5},
            3: {"name": "SET_3_INTRADAY_TREND", "htf_len": 10, "mtf_len": 3},
            4: {"name": "SET_4_INTRADAY_SCALP", "htf_len": 5, "mtf_len": 2}
        }
        self.friction_matrix = {"CRYPTO": 0.0012, "FOREX": 0.00015, "INDICES": 0.0004, "COMMODITIES": 0.0006}

    def evaluate_window_state(self, set_id: int, asset_class: str, current_close: float, trailing_rows: list) -> dict:
        """
        Derives structural alignments dynamically from real historical time arrays.
        """
        meta = self.window_matrix[set_id]
        
        # Extract closing price vectors from our historical row memory segment
        close_prices = [row[3] for row in trailing_rows]
        high_prices = [row[1] for row in trailing_rows]
        low_prices = [row[2] for row in trailing_rows]
        
        if len(close_prices) < meta["htf_len"]:
            return {"geometry_gate": "FAIL", "direction": "NO_TRADE"}

        # 📐 HTF STATE: Extract foundational structural direction across long lookbacks
        htf_basis = close_prices[-meta["htf_len"]]
        htf_bias = "BULLISH" if current_close >= htf_basis else "BEARISH"
        
        # 📐 MTF STATE: Detect intermediate pullback/realignment waves
        mtf_basis = close_prices[-meta["mtf_len"]]
        mtf_alignment = "BULLISH" if current_close >= mtf_basis else "BEARISH"
        
        # Core Entry Signal: HTF and MTF trends must align completely
        direction = "NO_TRADE"
        if htf_bias == "BULLISH" and mtf_alignment == "BULLISH":
            direction = "BUY"
        elif htf_bias == "BEARISH" and mtf_alignment == "BEARISH":
            direction = "SELL"
            
        # 📐 LTF STATE: Calculate structural stops from local price extremes
        local_window_high = max(high_prices[-3:])
        local_window_low = min(low_prices[-3:])
        
        friction_penalty = current_close * self.friction_matrix.get(asset_class, 0.0005)
        
        if direction == "BUY":
            final_sl = local_window_low - friction_penalty
            # Project targets relative to the true volatility depth of the lookback window
            volatility_depth = max(high_prices[-meta["mtf_len"]:] ) - min(low_prices[-meta["mtf_len"]:])
            final_tp = current_close + (max(volatility_depth, current_close * 0.005) * 2.2)
        elif direction == "SELL":
            final_sl = local_window_high + friction_penalty
            volatility_depth = max(high_prices[-meta["mtf_len"]:]) - min(low_prices[-meta["mtf_len"]:])
            final_tp = current_close - (max(volatility_depth, current_close * 0.005) * 2.2)
        else:
            final_sl = current_close
            final_tp = current_close

        # Verify geometric validity of the entry setup
        raw_risk = abs(current_close - final_sl)
        min_risk_allowed = current_close * 0.0005
        insulated_risk = max(raw_risk, min_risk_allowed)
        
        calculated_rr = abs(final_tp - current_close) / insulated_risk
        
        # Selection Gate: Enforce your strict minimum 1:4 risk-to-reward requirement
        geometry_gate = "PASS" if (calculated_rr >= 4.0 and direction != "NO_TRADE") else "FAIL"

        return {
            "set_id": set_id,
            "set_name": meta["name"],
            "entry_price": current_close,
            "final_sl": round(final_sl, 5),
            "final_tp": round(final_tp, 5),
            "calculated_rr": round(calculated_rr, 2),
            "geometry_gate": geometry_gate,
            "direction": direction
        }
