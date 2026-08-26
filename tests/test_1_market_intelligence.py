import unittest
import pandas as pd
import numpy as np
import sys
import os

# Ensure path is set
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.market_intelligence import IntelligenceEngine

class TestMarketIntelligence(unittest.TestCase):
    def test_engine_output(self):
        # Create proper Time-Series data
        idx = pd.date_range(start='2026-06-01', periods=100, freq='H')
        data = {
            'open': np.random.randn(100), 
            'high': np.random.randn(100), 
            'low': np.random.randn(100), 
            'close': np.random.randn(100)
        }
        df = pd.DataFrame(data, index=idx)
        
        engine = IntelligenceEngine()
        state = engine.calculate_intelligence(df)
        
        self.assertEqual(state.trend, "BULLISH")
        self.assertTrue(state.timestamp > 0)
        print(f"\n[DIAGNOSTIC] Market Intelligence Engine Output Verified: {state}")

if __name__ == '__main__':
    unittest.main()
