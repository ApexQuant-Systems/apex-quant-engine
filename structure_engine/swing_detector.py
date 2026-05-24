import pandas as pd
import numpy as np

class StructureEngine:
    def __init__(self, lookback=20):
        # Establish the liquidity pool (Swing Low) over the last 20 candles
        self.lookback = lookback

    def detect_swings(self, df):
        """
        Maps recent structural lows and gives the system a 3-candle memory of the sweep.
        """
        # Find the local structural low (excluding the current forming candle)
        df['local_low'] = df['low'].rolling(window=self.lookback).min().shift(1)
        
        # Flag the exact moment the sweep occurs (Wick below, Close above)
        df['Sweep_Event'] = np.where(
            (df['low'] < df['local_low']) & (df['close'] > df['local_low']), 
            True, 
            False
        )
        
        # --- SWEEP MEMORY ---
        # The system remembers the sweep for 3 hours, allowing the 
        # momentum displacement to occur AFTER the liquidity grab.
        df['Recent_Bullish_Sweep'] = df['Sweep_Event'].rolling(window=3).max() > 0

        return df
