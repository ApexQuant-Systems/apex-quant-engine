# filename: test_performance_engine_v1.py
import unittest
from analytics.performance_engine_v1 import ApexPerformanceEngineV1

class TestPerformanceEngineV1(unittest.TestCase):
    def setUp(self):
        self.analytics = ApexPerformanceEngineV1(starting_balance=1000.0)
        
        # Synthetic trade log: 2 Wins ($40 each), 2 Losses ($10 each)
        # Expected metrics: Win Rate 50%, Gross Profit $80, Gross Loss $20, PF 4.0, Net $60
        self.mock_trades = [
            {"symbol": "BTCUSDT", "outcome": "LOSS", "pnl": -10.0}, # Balance drops to 990 (DD 1%)
            {"symbol": "BTCUSDT", "outcome": "WIN", "pnl": 40.0},   # Balance rises to 1030 (New Peak)
            {"symbol": "BTCUSDT", "outcome": "LOSS", "pnl": -10.0}, # Balance drops to 1020 (DD from 1030 = ~0.97%)
            {"symbol": "BTCUSDT", "outcome": "WIN", "pnl": 40.0}    # Balance rises to 1060 (New Peak)
        ]

    def test_core_performance_metrics(self):
        report = self.analytics.generate_report(self.mock_trades)
        
        self.assertEqual(report["total_trades"], 4)
        self.assertEqual(report["win_rate_pct"], 50.0)
        self.assertEqual(report["profit_factor"], 4.0)
        self.assertEqual(report["total_pnl"], 60.0)
        self.assertEqual(report["ending_balance"], 1060.0)
        
        # Max Drawdown should be exactly 1.0% (The drop from 1000 to 990 on trade #1)
        self.assertAlmostEqual(report["max_drawdown_pct"], 1.0)

    def test_empty_ledger_handling(self):
        report = self.analytics.generate_report([])
        self.assertEqual(report["total_trades"], 0)
        self.assertEqual(report["profit_factor"], 0.0)

if __name__ == "__main__":
    unittest.main()
