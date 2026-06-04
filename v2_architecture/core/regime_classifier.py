import pandas as pd
import numpy as np

class MarketRegimeClassifier:
    """
    Layer 3.5: High-Fidelity Market Regime Engine.
    Quantifies structural trend velocity and volatility profiles 
    to filter out toxic range regimes before capital deployment.
    """
    @staticmethod
    def classify_regime(df_4h: pd.DataFrame, lookback=14):
        """
        Processes higher-timeframe data structures to define market states:
        - TRENDING_BULL
        - TRENDING_BEAR
        - CHOPPY_RANGE
        """
        if len(df_4h) < lookback + 5:
            return "CHOPPY_RANGE"
            
        closes = df_4h['close'].to_numpy()
        highs = df_4h['high'].to_numpy()
        lows = df_4h['low'].to_numpy()
        
        # 1. Calculate directional baseline velocity via fast exponential means
        ema_fast = df_4h['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema_slow = df_4h['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        
        # 2. Quantify physical volatility ratios using standard True Range envelopes
        tr = np.maximum(highs[1:] - lows[1:], 
                        np.maximum(abs(highs[1:] - closes[:-1]), 
                                   abs(lows[1:] - closes[:-1])))
        atr = pd.Series(tr).rolling(window=lookback).mean().iloc[-1]
        
        # 3. Calculate structural displacement momentum
        recent_range = highs[-lookback:].max() - lows[-lookback:].min()
        if atr == 0 or np.isnan(atr):
            return "CHOPPY_RANGE"
            
        volatility_ratio = recent_range / atr
        
        # --- REGIME INTERCEPTION LOGIC GATE ---
        if volatility_ratio < 4.5:
            # Low physical price expansion relative to average volatility proves range consolidation
            return "CHOPPY_RANGE"
        elif closes[-1] > ema_fast and ema_fast > ema_slow:
            return "TRENDING_BULL"
        elif closes[-1] < ema_fast and ema_fast < ema_slow:
            return "TRENDING_BEAR"
        else:
            return "CHOPPY_RANGE"

if __name__ == "__main__":
    print("[✓] Layer 3.5 MarketRegimeClassifier Module Compiled Successfully.")
