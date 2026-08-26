# filename: tests/test_4_risk_engine.py
import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.interfaces.contracts import TradePlan
from core.risk_engine import RiskEngine

class TestRiskEngine(unittest.TestCase):
    def test_position_sizing(self):
        engine = RiskEngine(risk_per_trade=0.01)
        
        # Scenario: $10,000 balance, Entry 50,000, SL 49,000 (Distance = 1,000)
        # Risk Amount = $100. Position Size = 100 / 1000 = 0.1
        plan = TradePlan("BTCUSDT", "BUY", 50000.0, 49000.0, 55000.0, time.time(), 5.0)
        assessment = engine.assess_trade(plan, 10000.0)
        
        self.assertTrue(assessment.allowed)
        self.assertEqual(assessment.risk_amount, 100.0)
        self.assertEqual(assessment.position_size, 0.1)
        
        print(f"\n[DIAGNOSTIC] Risk Engine Verified: Size={assessment.position_size} | RiskAmount={assessment.risk_amount}")

if __name__ == '__main__':
    unittest.main()
