# filename: test_execution_router_v1.py
import unittest
import os
import sqlite3
from datetime import datetime, timezone
from core.database.vault import ApexStorageVault
from core.interfaces.contracts import DecisionSnapshot, StrategyDecision, SignalDirection, MarketTrend
from execution.execution_router_v1 import ApexLocalExecutionRouterV1

class TestApexExecutionRouterV1(unittest.TestCase):
    def setUp(self):
        self.test_db = "data/execution_checkpoint_test.db"
        # Seed the structural database schema explicitly via the frozen Vault component
        self.vault = ApexStorageVault(db_path=self.test_db)
        self.router = ApexLocalExecutionRouterV1(db_path=self.test_db)

        # Build a valid top-down layout chain mockup token
        self.mock_decision = StrategyDecision(
            symbol="BTCUSDT",
            direction=SignalDirection.BUY,
            timeframe_a_bias=MarketTrend.BULLISH,
            timeframe_b_aligned=True,
            timeframe_c_triggered=True,
            convergence_score=95.0,
            structural_anchor_levels={"entry_price_fallback": 65000.0, "ltf_invalidation": 64000.0, "htf_target": 70000.0},
            timestamp=datetime.now(timezone.utc)
        )

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists(self.test_db + "-wal"):
            os.remove(self.test_db + "-wal")
        if os.path.exists(self.test_db + "-shm"):
            os.remove(self.test_db + "-shm")

    def test_approved_snapshot_ledger_commitment(self):
        # Scenario: Risk gate snapshot passes validation filters cleanly. 
        # Sizing calculations allocate a position footprint of 0.25 units.
        approved_snapshot = DecisionSnapshot(
            symbol="BTCUSDT", strategy_decision=self.mock_decision,
            news_gate_pass=True, spread_gate_pass=True, session_gate_pass=True,
            volatility_gate_pass=True, portfolio_gate_pass=True, proceed=True,
            rejection_reason=None, timestamp=datetime.now(timezone.utc)
        )

        receipt = self.router.execute_simulated_order(approved_snapshot, allocated_volume=0.25)
        self.assertTrue(receipt.startswith("FILLED_SUCCESS_"))

        # Query disk arrays to guarantee data rows exist inside the local vault
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT order_id, symbol, volume, status FROM orders")
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[1], "BTCUSDT")
        self.assertEqual(row[2], 0.25)
        self.assertEqual(row[3], "FILLED")

    def test_blocked_snapshot_short_circuit(self):
        # Scenario: Snapshot parameter arrives with proceed=False due to news gate trip
        blocked_snapshot = DecisionSnapshot(
            symbol="BTCUSDT", strategy_decision=self.mock_decision,
            news_gate_pass=False, spread_gate_pass=True, session_gate_pass=True,
            volatility_gate_pass=True, portfolio_gate_pass=True, proceed=False,
            rejection_reason="BLOCK_MACRO_ECONOMIC_NEWS_ACTIVE", timestamp=datetime.now(timezone.utc)
        )

        receipt = self.router.execute_simulated_order(blocked_snapshot, allocated_volume=0.25)
        self.assertEqual(receipt, "REJECTED_BY_RISK_FIREWALL")

        # Guarantee the query table metrics contain exactly 0 entries on disk
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 0)

if __name__ == "__main__":
    unittest.main()
