from core_vNext.execution.order_intent import OrderIntent

class RiskGuardian:
    """
    Enforces the absolute risk ceilings and minimum R:R constraints.
    """
    def __init__(self, max_risk_pct: float = 0.01, min_rr: float = 4.0):
        self.max_risk_pct = max_risk_pct
        self.min_rr = min_rr

    def evaluate_intent(self, intent: OrderIntent, current_equity: float, fee_rate: float = 0.0006) -> bool:
        """
        Evaluates an order intent. If it passes, it returns True and sets the expected_rr.
        If it fails, it returns False.
        """
        risk_dist = abs(intent.entry_price - intent.sl_price)
        reward_dist = abs(intent.tp_price - intent.entry_price)
        
        if risk_dist <= 0:
            return False

        # Apply basic fee approximation to penalize R:R slightly, as required by spec
        fee_cost = (intent.entry_price * fee_rate) + (intent.tp_price * fee_rate)
        
        net_reward = reward_dist - fee_cost
        net_risk = risk_dist + (intent.entry_price * fee_rate) + (intent.sl_price * fee_rate) # Risk is SL distance + entry/exit fees

        if net_risk <= 0:
            return False
            
        net_rr = net_reward / net_risk
        intent.expected_rr = net_rr

        if net_rr < self.min_rr:
            intent.status = "REJECTED_LOW_RR"
            return False
            
        if intent.risk_percentage > self.max_risk_pct:
            # We strictly cap the risk, but don't reject outright if it just asked for too much
            intent.risk_percentage = self.max_risk_pct

        intent.status = "APPROVED"
        return True
