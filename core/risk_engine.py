# filename: core/risk_engine.py
from core.interfaces.contracts import TradePlan, RiskAssessment
import time

class RiskEngine:
    def __init__(self, risk_per_trade: float = 0.01):
        self.risk_per_trade = risk_per_trade

    def assess_trade(self, plan: TradePlan, account_balance: float) -> RiskAssessment:
        # 1. Validate Stop Loss distance
        sl_distance = abs(plan.entry - plan.sl)
        
        if sl_distance <= 0:
            return RiskAssessment(
                symbol=plan.symbol,
                timestamp=float(time.time()),
                allowed=False,
                position_size=0.0,
                risk_amount=0.0,
                reason="INVALID_SL_DISTANCE"
            )

        # 2. Calculate Risk Amount (1% of balance)
        risk_amount = account_balance * self.risk_per_trade
        
        # 3. Calculate Position Size
        # Position Size = Risk Amount / SL Distance
        position_size = risk_amount / sl_distance
        
        return RiskAssessment(
            symbol=plan.symbol,
            timestamp=float(time.time()),
            allowed=True,
            position_size=position_size,
            risk_amount=risk_amount,
            reason="VALIDATED"
        )
