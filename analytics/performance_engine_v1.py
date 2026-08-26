# filename: analytics/performance_engine_v1.py
import logging
from typing import List, Dict, Any

class ApexPerformanceEngineV1:
    """
    Module 7: Performance Analytics Engine (Version 1.0.0).
    Consumes a ledger of closed trades and computes institutional-grade 
    performance metrics (Win Rate, Profit Factor, Max Drawdown).
    """
    def __init__(self, starting_balance: float = 1000.0):
        self.starting_balance = starting_balance
        self.logger = logging.getLogger("ApexPerformanceEngineV1")

    def generate_report(self, closed_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates the absolute performance statistics of a backtest run."""
        if not closed_trades:
            self.logger.warning("No closed trades provided to the analytics engine.")
            return self._empty_report()

        total_trades = len(closed_trades)
        wins = [t for t in closed_trades if t["pnl"] > 0]
        losses = [t for t in closed_trades if t["pnl"] <= 0]

        win_rate = (len(wins) / total_trades) * 100.0

        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        
        # Profit Factor: Gross Profit / Gross Loss. If zero losses, return infinity.
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        total_pnl = gross_profit - gross_loss
        ending_balance = self.starting_balance + total_pnl

        # Calculate Maximum Peak-to-Trough Drawdown
        peak_balance = self.starting_balance
        current_balance = self.starting_balance
        max_drawdown_pct = 0.0

        for trade in closed_trades:
            current_balance += trade["pnl"]
            if current_balance > peak_balance:
                peak_balance = current_balance
            
            # Drawdown from the highest recorded equity peak
            drawdown = (peak_balance - current_balance) / peak_balance * 100.0
            if drawdown > max_drawdown_pct:
                max_drawdown_pct = drawdown

        report = {
            "starting_balance": self.starting_balance,
            "ending_balance": ending_balance,
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_drawdown_pct
        }
        
        self.logger.info(
            f"Analytics Complete | Trades: {total_trades} | Win Rate: {win_rate:.1f}% | "
            f"PF: {profit_factor:.2f} | Max DD: {max_drawdown_pct:.2f}% | Net: ${total_pnl:.2f}"
        )
        return report

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "starting_balance": self.starting_balance,
            "ending_balance": self.starting_balance,
            "total_pnl": 0.0,
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0
        }
