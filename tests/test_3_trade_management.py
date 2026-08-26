# filename: tests/test_3_trade_management.py
import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.interfaces.contracts import StrategySignal
from core.trade_management import TradeManager

class TestTradeManager(unittest.TestCase):
    def test_rr_enforcement(self):
        manager = TradeManager(min_rr=4.0)
        signal = StrategySignal("BTCUSDT", time.time(), "BUY", "BULLISH", "READY", "TRIGGERED")
        
        # Test 1: Good RR (1:5) - Should be PENDING
        plan_pass = manager.calculate_plan(signal, 50000, 49000, 55000)
        self.assertEqual(plan_pass.status, "PENDING")
        self.assertEqual(plan_pass.risk_reward, 5.0)
        
        # Test 2: Bad RR (1:2) - Should be REJECTED_RR
        plan_fail = manager.calculate_plan(signal, 50000, 49000, 52000)
        self.assertEqual(plan_fail.status, "REJECTED_RR")
        
        print(f"\n[DIAGNOSTIC] Trade Manager RR Enforcement Verified.")

if __name__ == '__main__':
    unittest.main()
