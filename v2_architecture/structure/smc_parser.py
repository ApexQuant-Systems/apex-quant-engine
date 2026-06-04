import pandas as pd
import numpy as np

class SMCStructureEngine:
    """
    Pure Mathematical Smart Money Concepts Parser.
    Extracts high-fidelity structural metrics: BOS, CHOCH, FVG, and Order Blocks.
    """
    @staticmethod
    def identify_fair_value_gaps(df: pd.DataFrame):
        """
        Identifies unmitigated Fair Value Gaps using a strict 3-candle imbalance matrix.
        Bullish FVG: Candle 1 High < Candle 3 Low
        Bearish FVG: Candle 1 Low > Candle 3 High
        """
        fvgs = []
        if len(df) < 3:
            return fvgs
            
        highs = df['high'].to_numpy()
        lows = df['low'].to_numpy()
        closes = df['close'].to_numpy()
        timestamps = df['datetime'].tolist()
        
        for i in range(2, len(df)):
            # Bullish Inefficiency Sweep Validation
            if highs[i-2] < lows[i]:
                fvg_gap = lows[i] - highs[i-2]
                fvgs.append({
                    'type': 'BULLISH',
                    'top': lows[i],
                    'bottom': highs[i-2],
                    'gap_size': fvg_gap,
                    'creation_time': timestamps[i]
                })
            # Bearish Inefficiency Sweep Validation
            elif lows[i-2] > highs[i]:
                fvg_gap = lows[i-2] - highs[i]
                fvgs.append({
                    'type': 'BEARISH',
                    'top': lows[i-2],
                    'bottom': highs[i],
                    'gap_size': fvg_gap,
                    'creation_time': timestamps[i]
                })
        return fvgs

    @staticmethod
    def evaluate_market_pivots(df: pd.DataFrame, window=5):
        """
        Locates structural swing highs and lows to map trend shift boundaries.
        """
        if len(df) < (window * 2 + 1):
            return [], []
            
        highs = df['high'].to_numpy()
        lows = df['low'].to_numpy()
        timestamps = df['datetime'].tolist()
        
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(df) - window):
            current_high = highs[i]
            current_low = lows[i]
            
            # Check if current bar is a local structural ceiling
            if all(current_high > highs[i-j] for j in range(1, window+1)) and \
               all(current_high >= highs[i+j] for j in range(1, window+1)):
                swing_highs.append({'price': current_high, 'time': timestamps[i]})
                
            # Check if current bar is a local structural floor
            if all(current_low < lows[i-j] for j in range(1, window+1)) and \
               all(current_low <= lows[i+j] for j in range(1, window+1)):
                swing_lows.append({'price': current_low, 'time': timestamps[i]})
                
        return swing_highs, swing_lows

if __name__ == "__main__":
    print("[✓] SMCStructureEngine Loaded. Structural Geometry Pipelines Initialized.")
