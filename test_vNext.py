import sys
import os
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core_vNext.strategy.unified_strategy import UnifiedStrategy

def run_test():
    # Mock data
    np.random.seed(42)
    dates = pd.date_range('2026-01-01', periods=100, freq='D')
    closes = np.cumsum(np.random.randn(100)) + 100
    highs = closes + np.random.rand(100) * 2
    lows = closes - np.random.rand(100) * 2
    
    df = pd.DataFrame({
        'timestamp': [d.timestamp() for d in dates],
        'open': closes - 0.5,
        'high': highs,
        'low': lows,
        'close': closes
    })
    
    print("Initializing strategy...")
    strategy = UnifiedStrategy("BTC", "SET_3")
    
    print("Processing multi-horizon mock data...")
    strategy.process_multi_horizon(df, df, df)
    
    print(f"Final State: {strategy.fsm.state}")
    print(f"HTF Trend: {strategy.htf_swings.current_trend}")
    print(f"Active Intent: {strategy.fsm.active_intent}")
    print("Test passed without exceptions.")

if __name__ == "__main__":
    run_test()
