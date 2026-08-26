from typing import Dict, List, Optional
import time

class PortfolioHeatGovernor:
    """
    Centralized Institutional Portfolio Risk & Drawdown Governor.
    Enforces maximum concurrent risk across all assets and daily drawdown circuit breakers.
    """
    def __init__(self, max_total_portfolio_heat_pct: float = 0.025, max_daily_drawdown_pct: float = 0.030):
        self.max_total_portfolio_heat_pct = max_total_portfolio_heat_pct
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        
        self.active_positions: Dict[str, dict] = {}
        self.daily_starting_equity: float = 0.0
        self.current_day: str = ""
        self.is_circuit_tripped: bool = False

    def check_and_update_day(self, current_date_str: str, current_equity: float):
        if current_date_str != self.current_day:
            self.current_day = current_date_str
            self.daily_starting_equity = current_equity
            self.is_circuit_tripped = False

    def can_open_new_trade(self, asset: str, proposed_risk_pct: float, current_equity: float, current_date_str: str) -> bool:
        self.check_and_update_day(current_date_str, current_equity)
        
        # Check Daily Drawdown Circuit Breaker
        if self.daily_starting_equity > 0:
            daily_dd = (self.daily_starting_equity - current_equity) / self.daily_starting_equity
            if daily_dd >= self.max_daily_drawdown_pct:
                self.is_circuit_tripped = True
                return False
                
        if self.is_circuit_tripped:
            return False

        # Calculate current total heat
        current_heat = sum(pos.get("risk_pct", 0.0) for pos in self.active_positions.values())
        if current_heat + proposed_risk_pct > self.max_total_portfolio_heat_pct:
            return False

        return True

    def register_position(self, asset: str, trade_id: str, risk_pct: float, dollar_risk: float):
        self.active_positions[trade_id] = {
            "asset": asset,
            "risk_pct": risk_pct,
            "dollar_risk": dollar_risk,
            "timestamp": time.time()
        }

    def close_position(self, trade_id: str):
        if trade_id in self.active_positions:
            del self.active_positions[trade_id]
