import pandas as pd
import numpy as np

class DisplacementEngine:
    def __init__(self, lookback=5, threshold_multiplier=1.5):
        self.lookback = lookback
        self.multiplier = threshold_multiplier

    def validate_displacement(self, df: pd.DataFrame) -> dict:
        """
        Validates whether the latest closed candle exhibits significant institutional momentum
        compared to the recent local context window.
        """
        if len(df) < self.lookback + 1:
            return {"displacement": False, "ratio": 0.0, "reason": "Insufficient history"}

        # Calculate absolute candle bodies (|Close - Open|)
        bodies = (df['close'] - df['open']).abs()
        
        # Isolate the current candle body and the preceding context window
        current_body = bodies.iloc[-1]
        historical_bodies = bodies.iloc[-(self.lookback + 1):-1]
        
        # Calculate the baseline average historical body size
        mean_historical_body = historical_bodies.mean()
        
        if mean_historical_body == 0:
            return {"displacement": False, "ratio": 0.0, "reason": "Zero volatility baseline"}
            
        # Compute the velocity multiplier ratio
        ratio = current_body / mean_historical_body
        is_displaced = ratio >= self.multiplier
        
        return {
            "displacement": is_displaced,
            "ratio": round(ratio, 2),
            "current_body": round(current_body, 2),
            "avg_body": round(mean_historical_body, 2)
        }
