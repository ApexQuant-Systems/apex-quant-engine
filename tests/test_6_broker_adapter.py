# filename: tests/test_6_broker_adapter.py
import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.interfaces.contracts import TradePlan
from core.execution.vantage_adapter import VantageAdapter

class TestBrokerAdapter(unittest.TestCase):
    def test_order_execution_flow(self):
        adapter = VantageAdapter()
        plan = TradePlan("BTCUSDT", "BUY", 50000.0, 49000.0, 55000.0, time.time(), 5.0)
        
        # Test connection and order placement
        self.assertTrue(adapter.connect())
        order_id = adapter.place_order(plan)
        
        self.assertIn("ORDER_SENT", order_id)
        print(f"\n[DIAGNOSTIC] Broker Adapter Flow Verified: {order_id}")

if __name__ == '__main__':
    unittest.main()
