import unittest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.market_intelligence import IntelligenceEngine

class TestStructuralIntelligence(unittest.TestCase):
    def test_bos_logic(self):
        # Create a price series where the final close (105) breaks the previous High (103)
        idx = pd.date_range(start='2026-06-01', periods=20, freq='h')
        data = {
            'open': [100]*20, 
            'high': [100, 101, 100, 102, 101, 103]*3 + [100, 100],
            'low': [99]*20, 
            'close': [99, 100, 99, 101, 100, 105]*3 + [100, 105] # Ended with 105 to trigger BOS
        }
        df = pd.DataFrame(data, index=idx)
        
        engine = IntelligenceEngine(lookback=1, atr_mult=0.01)
        state = engine.calculate_intelligence(df)
        
        # Now current_close (105) > 103 + ATR, so it returns BULLISH
        self.assertEqual(state.trend, "BULLISH")
        print(f"\n[DIAGNOSTIC] Structural Engine Verified Trend: {state.trend}")

if __name__ == '__main__':
    unittest.main()
