# filename: test_backtest_replay_loop.py
import unittest
from datetime import datetime, timezone
from filters.risk_filters_engine_v1 import ApexRiskFiltersEngineV1
from core.interfaces.contracts import TradePlan, SignalDirection
from backtesting.historical_replay import ApexHistoricalReplayEngine

class TestBacktestPipelineLoop(unittest.TestCase):
    def setUp(self):
        self.risk_filters = ApexRiskFiltersEngineV1(current_account_balance=1000.0)
        
        # Build synthetic historical time series matrix representing consecutive upward movements
        self.historical_dataset = [
            {"timestamp": "2026-01-01 00:00:00", "close": 100.0, "high": 101.0, "low": 99.0},
            {"timestamp": "2026-01-01 01:00:00", "close": 101.0, "high": 102.0, "low": 100.0},
            {"timestamp": "2026-01-01 02:00:00", "close": 102.0, "high": 103.0, "low": 101.0},
            {"timestamp": "2026-01-01 03:00:00", "close": 103.0, "high": 104.0, "low": 102.0},
            {"timestamp": "2026-01-01 04:00:00", "close": 104.0, "high": 105.0, "low": 103.0},
            {"timestamp": "2026-01-01 05:00:00", "close": 105.0, "high": 106.0, "low": 104.0},
            {"timestamp": "2026-01-01 06:00:00", "close": 110.0, "high": 112.0, "low": 109.0} # Breakout candle
        ]

    def test_risk_engine_exposes_lot_size(self):
        plan = TradePlan(
            symbol="BTCUSDT", direction=SignalDirection.BUY,
            entry_price=100.0, stop_loss=90.0, take_profit=150.0,
            risk_reward_ratio=5.0, is_valid=True, timestamp=datetime.now(timezone.utc)
        )
        # Sizing math evaluation: Risk distance = 10. Balance = 1000. 1% Risk = $10.
        # Allocated size should compute precisely to 1.0 units.
        snapshot = self.risk_filters.evaluate_execution_safety(plan, active_portfolio_symbols=[])
        
        self.assertTrue(snapshot.proceed)
        self.assertEqual(snapshot.allocated_lot_size, 1.0) # FIXED: Sizing variable is captured and exposed
        self.assertEqual(snapshot.cash_at_risk, 10.0)

    def test_historical_replay_execution_loop(self):
        replay_engine = ApexHistoricalReplayEngine(asset_symbol="ETHUSDT", account_balance=5000.0)
        results = replay_engine.execute_replay_pass(self.historical_dataset)
        
        self.assertEqual(results["status"], "COMPLETED")
        self.assertEqual(results["total_bars_replayed"], 1) # First valid cross frame pass execution index
        # Verify signal outputs are stored cleanly in local state lists instead of hitting disk SQL triggers prematurely
        self.assertTrue(isinstance(replay_engine.generated_trade_signals, list))

if __name__ == "__main__":
    unittest.main()
