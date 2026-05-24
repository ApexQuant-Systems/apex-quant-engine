# risk_engine/order_sizer.py
import numpy as np

class InstitutionalRiskFirewall:
    def __init__(self, account_balance: float, base_risk_pct: float = 0.01):
        self.account_balance = account_balance
        self.base_risk_pct = base_risk_pct
        
    def calculate_protected_size(self, entry_price: float, stop_loss: float, estimated_slippage_pct: float, current_correlation: float, active_exposure: bool):
        """
        Calculates position sizing adjusted for execution friction and asset correlation heat.
        """
        # Step 1: Calculate raw capital at risk
        allowed_risk_capital = self.account_balance * self.base_risk_pct
        
        # Step 2: Apply correlation penalty if we are already exposed to a highly cointegrated asset (e.g., BTC vs ETH)
        if active_exposure and current_correlation > 0.80:
            print("System Governance: High cross-asset correlation detected. Cutting risk capital allocation by 50%.")
            allowed_risk_capital *= 0.5
            
        # Step 3: Adjust the distance to stop loss to account for slippage drag during execution execution
        raw_stop_distance = abs(entry_price - stop_loss)
        slippage_buffer = entry_price * estimated_slippage_pct
        effective_stop_distance = raw_stop_distance + slippage_buffer
        
        if effective_stop_distance <= 0:
            return 0.0
            
        # Step 4: Output the precise asset unit volume
        position_units = allowed_risk_capital / effective_stop_distance
        return round(position_units, 4)

if __name__ == "__main__":
    firewall = InstitutionalRiskFirewall(account_balance=10000.0)
    print("Testing Sizer Risk Matrix Allocation...")
    # Simulating buying BTC at 65000 with a stop at 64000, 0.05% slippage, with active highly correlated positions
    size = firewall.calculate_protected_size(
        entry_price=65000, 
        stop_loss=64000, 
        estimated_slippage_pct=0.0005, 
        current_correlation=0.87, 
        active_exposure=True
    )
    print(f"Authorized Position Units: {size} units")
