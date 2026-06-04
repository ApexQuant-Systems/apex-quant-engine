import os
import sys
import numpy as np

class InstitutionalRiskEngine:
    """
    Layer 5: Enterprise Portfolio & Risk Management System.
    Calculates exact risk allocations, normalizes for contract steps, 
    and handles global portfolio heat clamps.
    """
    def __init__(self, risk_per_trade=0.01, max_portfolio_heat=0.03):
        self.risk_per_trade = risk_per_trade
        self.max_portfolio_heat = max_portfolio_heat
        
        # Core correlation clusters to isolate sector risk exposure
        self.correlation_groups = {
            'CRYPTO_BETA': ['BTC', 'ETH', 'SOL', 'AVAX'],
            'USD_MAJORS': ['EURUSD', 'GBPUSD', 'AUDUSD']
        }

    def calculate_position_size(self, account_balance, entry_price, sl_price, instrument_config):
        """
        Calculates exact mathematical order quantities. Enforces an absolute 
        Friction Guard to protect micro-accounts from exchange contract floors.
        """
        # Extract instrument specific limitations
        min_lot = instrument_config.get('min_lot', 0.001)
        step_size = instrument_config.get('step_size', 0.001)
        notional_min = instrument_config.get('notional_min', 5.0) # e.g., $5 absolute order floor
        
        # 1. Quantify exact dollar value exposure rule
        capital_at_risk = account_balance * self.risk_per_trade
        
        # 2. Calculate point distance risk delta
        risk_per_unit = abs(entry_price - sl_price)
        if risk_per_unit == 0:
            return 0.0
            
        # 3. Raw size generation
        raw_position_size = capital_at_risk / risk_per_unit
        
        # 4. Step-size precision normalization
        precision_multiplier = 1.0 / step_size
        normalized_size = np.floor(raw_position_size * precision_multiplier) / precision_multiplier
        
        # --- FRICTION GUARD FIREWALL ---
        # Verify if the normalized target fits within absolute broker limitations
        notional_value = normalized_size * entry_price
        
        if normalized_size < min_lot or notional_value < notional_min:
            # For micro accounts ($10), if 1% risk falls below exchange execution minimums,
            # the system aborts the trade execution sequence entirely to isolate rules from decay.
            return 0.0
            
        return float(normalized_size)

    def evaluate_portfolio_admission(self, new_asset, active_positions):
        """
        Audits current sector clustering to ensure max portfolio heat limit is preserved
        and stops highly correlated assets from stacking systemic sector exposure.
        """
        # 1. Total Heat Clamp check
        current_heat = len(active_positions) * self.risk_per_trade
        if current_heat + self.risk_per_trade > self.max_portfolio_heat:
            return False, "ADMISSION_DENIED: Portfolio Total Heat Cap Intercept"
            
        # 2. Correlation Control Matrix check
        new_base = new_asset.split('/')[0].split('USDT')[0]
        
        # Identify group sector allocation
        target_cluster = None
        for group_name, assets in self.correlation_groups.items():
            if new_base in assets:
                target_cluster = assets
                break
                
        if target_cluster:
            active_cluster_count = 0
            for active_trade in active_positions:
                active_base = active_trade.split('/')[0].split('USDT')[0]
                if active_base in target_cluster:
                    active_cluster_count += 1
                    
            # Rule: Hard limit of 2 concurrent positions inside a single correlation cluster
            if active_cluster_count >= 2:
                return False, f"ADMISSION_DENIED: Sector Concentration Risk Level on {group_name}"
                
        return True, "ADMISSION_GRANTED: Risk Profiling Cleared"

if __name__ == "__main__":
    print("[⚡ RISK SYSTEM] Running local verification protocols...")
    engine = InstitutionalRiskEngine(risk_per_trade=0.01, max_portfolio_heat=0.03)
    
    # Test Instrument configuration parameters for a Standard Bitcoin Futures Asset
    btc_config = {'min_lot': 0.001, 'step_size': 0.001, 'notional_min': 5.0}
    
    # Scenario A: Processing a $100,000 Institutional Capital Layer Account Balance
    whale_size = engine.calculate_position_size(100000.0, 68000.0, 67500.0, btc_config)
    print(f" [✓] Whale Position Size ($100k Account, 1% Risk): {whale_size} BTC")
    
    # Scenario B: Processing an extreme Micro Capital Sheet ($10 Account Balance)
    micro_size = engine.calculate_position_size(10.0, 68000.0, 67500.0, btc_config)
    print(f" [✓] Micro Position Size ($10 Account, 1% Risk - Friction Guard Triggered): {micro_size} BTC")
    
    # Scenario C: Sector Correlation Interception Test Matrix
    mock_active_portfolio = ['BTC/USDT', 'ETH/USDT']
    allowed, message = engine.evaluate_portfolio_admission('SOL/USDT', mock_active_portfolio)
    print(f" [✓] Cluster Validation Result: {message}")
