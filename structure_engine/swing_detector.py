import pandas as pd
import numpy as np

class StructureEngine:
    def __init__(self, lookback=20):
        # We look back 20 periods to establish the "Swing Low" liquidity pool
        self.lookback = lookback

    def detect_swings(self, df):
        """
        Maps recent structural lows and flags mathematically pure Liquidity Sweeps.
        """
        # Step 1: Find the local structural low (excluding the current forming candle)
        df['local_low'] = df['low'].rolling(window=self.lookback).min().shift(1)
        
        # Step 2: Define the Bullish Liquidity Sweep
        # Condition A: The candle wicks below the established local low (Triggering Stops)
        # Condition B: The candle closes back ABOVE the local low (Institutional Absorption)
        df['Bullish_Sweep'] = np.where(
            (df['low'] < df['local_low']) & (df['close'] > df['local_low']), 
            True, 
            False
        )

        return df
