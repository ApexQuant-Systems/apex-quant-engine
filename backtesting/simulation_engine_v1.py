# filename: backtesting/simulation_engine_v1.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from core.interfaces.contracts import DecisionSnapshot, SignalDirection

class ApexSimulationEngineV1:
    """
    Module 6: Simulation Engine (Version 1.0.0).
    A lookahead-free sandbox matching engine. Holds approved snapshots as 
    'Open Positions' and checks them bar-by-bar against high/low extremes 
    to trigger SL or TP closures.
    """
    def __init__(self, starting_balance: float = 1000.0):
        self.starting_balance = starting_balance
        self.current_balance = starting_balance
        self.open_positions: List[Dict[str, Any]] = []
        self.closed_trades: List[Dict[str, Any]] = []
        self.logger = logging.getLogger("ApexSimulationEngineV1")

    def register_approved_signal(self, snapshot: DecisionSnapshot):
        """Accepts a risk-approved trade plan and stages it as an active open position."""
        if not snapshot.proceed:
            return

        plan = snapshot.trade_plan
        position = {
            "symbol": snapshot.symbol,
            "direction": plan.direction,
            "entry_price": plan.entry_price,
            "stop_loss": plan.stop_loss,
            "take_profit": plan.take_profit,
            "volume": snapshot.allocated_lot_size,
            "cash_at_risk": snapshot.cash_at_risk,
            "open_time": snapshot.timestamp,
            "status": "OPEN"
        }
        self.open_positions.append(position)
        self.logger.info(f"[{snapshot.symbol}] MOCK POSITION OPENED: {plan.direction.value} @ {plan.entry_price}")

    def process_tick(self, candle: Dict[str, Any]):
        """
        Steps through a new candle and checks if any open positions 
        intersected their geometric death/target boundaries.
        """
        high = float(candle["high"])
        low = float(candle["low"])
        timestamp = candle.get("timestamp", datetime.now(timezone.utc))

        remaining_positions = []

        for pos in self.open_positions:
            closed = False
            outcome = ""
            pnl = 0.0

            if pos["direction"] == SignalDirection.BUY:
                # Pessimistic assumption: If a single bar sweeps both SL and TP, SL triggers first to protect capital logic.
                if low <= pos["stop_loss"]:
                    closed = True
                    outcome = "LOSS"
                    pnl = -pos["cash_at_risk"]
                elif high >= pos["take_profit"]:
                    closed = True
                    outcome = "WIN"
                    # Reward = Risk * RR Ratio. Since volume = cash_at_risk / distance, PnL is exact.
                    price_diff = pos["take_profit"] - pos["entry_price"]
                    pnl = price_diff * pos["volume"]

            elif pos["direction"] == SignalDirection.SELL:
                if high >= pos["stop_loss"]:
                    closed = True
                    outcome = "LOSS"
                    pnl = -pos["cash_at_risk"]
                elif low <= pos["take_profit"]:
                    closed = True
                    outcome = "WIN"
                    price_diff = pos["entry_price"] - pos["take_profit"]
                    pnl = price_diff * pos["volume"]

            if closed:
                self.current_balance += pnl
                pos["status"] = "CLOSED"
                pos["outcome"] = outcome
                pos["pnl"] = pnl
                pos["close_time"] = timestamp
                self.closed_trades.append(pos)
                self.logger.info(f"[{pos['symbol']}] MOCK POSITION CLOSED: {outcome} | PnL: {pnl:.2f} | Balance: {self.current_balance:.2f}")
            else:
                remaining_positions.append(pos)

        # Update tracking list to only retain unresolved setups
        self.open_positions = remaining_positions
