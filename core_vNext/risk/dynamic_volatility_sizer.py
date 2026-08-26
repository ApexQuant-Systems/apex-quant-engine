import numpy as np

class DynamicVolatilitySizer:
    """
    Institutional Inverse-ATR Volatility Position Sizer.
    Normalizes trade risk so high-volatility spikes downsize risk automatically,
    compressing maximum drawdowns to strict institutional levels (<8-10%).
    """
    def __init__(self, target_base_risk_pct: float = 0.015, min_risk_pct: float = 0.005, max_risk_pct: float = 0.020):
        self.target_base_risk_pct = target_base_risk_pct
        self.min_risk_pct = min_risk_pct
        self.max_risk_pct = max_risk_pct

    def compute_volatility_adjusted_size(self, 
                                          current_equity: float, 
                                          entry_price: float, 
                                          sl_price: float, 
                                          current_atr: float, 
                                          median_atr: float) -> tuple[float, float, float]:
        """
        Returns:
            (position_size, dollar_risk, effective_risk_pct)
        """
        risk_dist = abs(entry_price - sl_price)
        if risk_dist <= 0 or current_equity <= 0:
            return 0.0, 0.0, 0.0

        # Volatility normalization factor = Median ATR / Current ATR
        if current_atr > 0 and median_atr > 0:
            vol_multiplier = np.clip(median_atr / current_atr, 0.4, 1.5)
        else:
            vol_multiplier = 1.0

        effective_risk_pct = np.clip(self.target_base_risk_pct * vol_multiplier, self.min_risk_pct, self.max_risk_pct)
        dollar_risk = current_equity * effective_risk_pct
        position_size = dollar_risk / risk_dist

        return position_size, dollar_risk, effective_risk_pct
