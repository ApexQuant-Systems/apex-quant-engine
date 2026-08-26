# filename: execution/execution_router_v1.py
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from config.global_config import GLOBAL_CONFIG
from core.interfaces.contracts import DecisionSnapshot, ExecutionOrder

class ApexLocalExecutionRouterV1:
    """
    Module 5: Local Execution Router & Matcher Simulator (Version 1.0.0).
    Intercepts risk-cleared snapshots and updates local database ledgers.
    Completely isolated from real exchange APIs to safeguard sandboxed validation testing.
    """
    def __init__(self, db_path: str = GLOBAL_CONFIG.DB_PATH):
        self.db_path = db_path
        self.logger = logging.getLogger("ApexLocalExecutionRouterV1")

    def execute_simulated_order(self, snapshot: DecisionSnapshot, allocated_volume: float) -> str:
        """
        Processes the execution pass snapshot. If allowed, generates an isolated order receipt
        and records it securely inside the SQLite vault files.
        """
        symbol = snapshot.symbol
        decision = snapshot.strategy_decision

        # Gate 0: Block processing instantly if the risk firewall tripped to False
        if not snapshot.proceed:
            reason = snapshot.rejection_reason or "RISK_GATEWAY_DENIED"
            self.logger.error(f"[{symbol}] Execution aborted: Directive blocked by Risk Firewall. Reason: {reason}")
            return "REJECTED_BY_RISK_FIREWALL"

        # Gate 1: Zero volume protection barrier
        if allocated_volume <= 0.0:
            self.logger.error(f"[{symbol}] Execution aborted: Calculated allocation sizing holds zero footprint.")
            return "REJECTED_INVALID_VOLUME"

        # Step 2: Formulate standard internal execution tokens using uuid generation hashes
        order_id = f"APEX-MOCK-{uuid.uuid4().hex[:8].upper()}"
        direction_str = decision.direction.value # Extract string token: "BUY" or "SELL"
        
        # Pull structural parameters from strategy anchor dictionaries passed downward
        anchors = decision.structural_anchor_levels
        entry_p = anchors.get("entry_price_fallback", 0.0)
        stop_p = anchors.get("ltf_invalidation", 0.0)
        target_p = anchors.get("htf_target", 0.0)

        # Step 3: Atomic database insertion transaction loop via SQLite WAL channels
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        try:
            cursor.execute("""
                INSERT INTO orders (order_id, symbol, direction, volume, entry_price, stop_loss, take_profit, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, symbol, direction_str, float(allocated_volume),
                float(entry_p), float(stop_p), float(target_p), "FILLED", timestamp_str
            ))
            conn.commit()
            self.logger.info(f" Successfully matched simulated order [{order_id}] for {symbol} -> Committed to local ledger.")
            return f"FILLED_SUCCESS_{order_id}"
        except sqlite3.Error as e:
            self.logger.critical(f"Database insertion write crash encountered: {str(e)}")
            return "EXECUTION_DATABASE_ERROR"
        finally:
            conn.close()
