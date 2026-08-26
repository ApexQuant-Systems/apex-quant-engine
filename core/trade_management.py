# filename: core/trade_management.py
from core.interfaces.contracts import StrategySignal, MarketState, TradePlan

class TradeManager:
    def __init__(self, min_rr: float = 4.0):
        self.min_rr = min_rr

    def calculate_plan(self, signal: StrategySignal, current_price: float, sl: float, tp: float) -> TradePlan:
        """
        Translates a signal into a TradePlan.
        Enforces 1:4 RR minimum.
        """
        # Calculate Risk and Reward
        risk = abs(current_price - sl)
        reward = abs(tp - current_price)
        
        rr = reward / risk if risk != 0 else 0
        
        if rr < self.min_rr:
            return TradePlan(
                symbol=signal.symbol,
                direction=signal.action,
                entry=current_price,
                sl=sl,
                tp=tp,
                timestamp=signal.timestamp,
                risk_reward=rr,
                status="REJECTED_RR"
            )
            
        return TradePlan(
            symbol=signal.symbol,
            direction=signal.action,
            entry=current_price,
            sl=sl,
            tp=tp,
            timestamp=signal.timestamp,
            risk_reward=rr,
            status="PENDING"
        )
