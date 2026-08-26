# filename: test_risk_filters_v1.py
import unittest
from datetime import datetime, timezone
from core.interfaces.contracts import TradePlan, SignalDirection, DecisionSnapshot
from filters.risk_filters_engine_v1 import ApexRiskFiltersEngineV1

class TestApexRiskFiltersEngineV1(unittest.TestCase):
    def setUp(self):
        # Initialize with a standard $1,000 baseline account equity ledger
        self.risk_engine = ApexRiskFiltersEngineV1(current_account_balance=1000.0)
        
        # Seed a valid structural Buy Trade Plan layout (Risk distance = $1,000)
        self.valid_plan = TradePlan(
            symbol="BTCUSDT",
            direction=SignalDirection.BUY,
            entry_price=65000.0,
            stop_loss=64000.0,
            take_profit=70000.0,
            risk_reward_ratio=5.0,
            is_valid=True,
            timestamp=datetime.now(timezone.utc)
        )

    def test_validated_position_sizing_pass(self):
        # Scenario: Risk distance = 1000. Balance = 1000. Capped risk parameter = 1% ($10).
        # Target lot size footprint must resolve precisely to 0.01 units.
        snapshot = self.risk_engine.evaluate_execution_safety(
            self.valid_plan, active_portfolio_symbols=["ETHUSDT"]
        )
        
        self.assertTrue(snapshot.proceed)
        self.assertIsNone(snapshot.rejection_reason)
        self.assertTrue(snapshot.news_gate_pass)

    def test_news_gate_interception(self):
        # Scenario: Incoming signal matches parameters, but a high-impact news window is flagged active
        snapshot = self.risk_engine.evaluate_execution_safety(
            self.valid_plan, active_portfolio_symbols=[], is_macro_news_active=True
        )
        
        self.assertFalse(snapshot.proceed)
        self.assertEqual(snapshot.rejection_reason, "BLOCK_MACRO_ECONOMIC_NEWS_ACTIVE")
        self.assertFalse(snapshot.news_gate_pass)

    def test_systemic_correlation_clamp_interception(self):
        # Scenario: Portfolio already holds 3 highly correlated crypto assets. Additional allocations must be blocked.
        active_exposures = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        snapshot = self.risk_engine.evaluate_execution_safety(
            self.valid_plan, active_portfolio_symbols=active_exposures
        )
        
        self.assertFalse(snapshot.proceed)
        self.assertEqual(snapshot.rejection_reason, "BLOCK_MAX_SYSTEMIC_CORRELATION_BREACHED")
        self.assertFalse(snapshot.portfolio_gate_pass)

if __name__ == "__main__":
    unittest.main()
