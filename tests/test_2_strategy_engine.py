# filename: tests/test_2_strategy_engine.py
import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.market_intelligence import MarketState
from core.strategy_engine import StrategyEngine

class TestStrategyEngine(unittest.TestCase):
    def test_bullish_alignment(self):
        # 1. HTF Bullish Bias
        htf = MarketState(
            symbol="BTCUSDT", timeframe="1D", trend="BULLISH", structure="HH",
            phase="EXPANSION", keyzones=["OB_1"], liquidity=[], strength=90.0, 
            confidence=95.0, invalidated=False, timestamp=time.time()
        )
        
        # 2. MTF Pullback to Keyzone
        mtf = MarketState(
            symbol="BTCUSDT", timeframe="1H", trend="BULLISH", structure="HL",
            phase="PULLBACK", keyzones=["OB_1"], liquidity=[], strength=80.0, 
            confidence=85.0, invalidated=False, timestamp=time.time()
        )
        
        # 3. LTF Entry Trigger (Sweep)
        ltf = MarketState(
            symbol="BTCUSDT", timeframe="15M", trend="BULLISH", structure="HH",
            phase="EXPANSION", keyzones=[], liquidity=["EQH_SWEEP"], strength=70.0, 
            confidence=80.0, invalidated=False, timestamp=time.time()
        )
        
        engine = StrategyEngine()
        signal = engine.generate_signal(htf, mtf, ltf)
        
        print(f"\n[DIAGNOSTIC] Strategy Signal Generated: {signal.action}")
        self.assertEqual(signal.action, "BUY")

if __name__ == '__main__':
    unittest.main()
