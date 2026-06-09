import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Enforce parent project root path containment to unlock absolute multi-asset module pathing
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from v2_architecture.unified_portfolio_validator import UnifiedPortfolioValidator

class ExecutionCostSimulator(UnifiedPortfolioValidator):
    """
    Layer 9.3: Microstructure Friction & Slippage Simulation Engine.
    Inherits the pristine un-aliased multi-asset trade ledger and applies
    maker/taker fees, spread haircuts, and funding rate decay to test edge survival.
    """
    def __init__(self, initial_balance=30000.0):
        super().__init__(initial_balance)

    def simulate_frictional_timeline(self, global_ledger, weights, fee_bps, slippage_bps, funding_hourly_bps, target_years):
        """
        Executes portfolio simulation while systematically reducing returns by execution cost vectors.
        """
        balance = self.initial_balance
        peak = balance
        max_dd = 0.0
        wins, losses = 0, 0
        total_pnl_won, total_pnl_lost = 0.0, 0.0
        
        total_fees_paid = 0.0
        total_slippage_lost = 0.0
        total_funding_paid = 0.0

        for trade in global_ledger:
            if trade['year'] not in target_years: continue

            if balance > peak: peak = balance
            current_dd = (peak - balance) / peak
            if current_dd > max_dd: max_dd = current_dd

            # --- OS PIECEWISE FIREWALL GATE ---
            if current_dd >= 0.25: risk_scale = 0.0000
            elif current_dd >= 0.20: risk_scale = 0.0025
            elif current_dd >= 0.15: risk_scale = 0.0050
            elif current_dd >= 0.10: risk_scale = 0.0075
            else: risk_scale = 0.0100

            asset_weight = weights.get(trade['asset'], 0.0)
            risk_capital = balance * risk_scale * asset_weight
            
            if risk_capital <= 0: continue

            # --- MICROSTRUCTURE COST CALCULATION ---
            approx_leverage = 3.0
            notional_position_size = risk_capital * approx_leverage

            # 1. Exchange Commission (Entry Taker + Exit Taker)
            fee_cost = notional_position_size * (fee_bps / 10000.0) * 2.0
            
            # 2. Market Spread & Order Book Slippage Haircut
            slippage_cost = notional_position_size * (slippage_bps / 10000.0) * 2.0
            
            # 3. Capital Funding Rent (Estimated average trade hold time ~ 4 hours)
            estimated_hours_held = 4.0
            funding_cost = notional_position_size * (funding_hourly_bps / 10000.0) * estimated_hours_held

            total_friction_loss = fee_cost + slippage_cost + funding_cost
            
            raw_trade_pnl = risk_capital * trade['risk_mult']
            net_trade_pnl = raw_trade_pnl - total_friction_loss
            balance += net_trade_pnl

            total_fees_paid += fee_cost
            total_slippage_lost += slippage_cost
            total_funding_paid += funding_cost

            if net_trade_pnl > 0:
                wins += 1; total_pnl_won += net_trade_pnl
            else:
                losses += 1; total_pnl_lost += abs(net_trade_pnl)

        total_trades = wins + losses
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0.0
        net_pf = total_pnl_won / total_pnl_lost if total_pnl_lost > 0 else total_pnl_won
        
        return {
            'trades': total_trades, 'win_rate': win_rate, 'pf': net_pf, 'max_dd': max_dd * 100,
            'final_balance': balance, 'fees': total_fees_paid, 'slippage': total_slippage_lost, 'funding': total_funding_paid
        }

    def run_friction_stress_test(self):
        print("==========================================================================================")
        print(" 🔍 APEX QUANT OS CORE: REAL-WORLD TRANSACTION COST & SLIPPAGE FRICTION AUDIT")
        print("==========================================================================================")
        
        global_ledger = []
        for asset in self.assets:
            trades = self.extract_cartridge_trades(asset)
            global_ledger.extend(trades)
        global_ledger = sorted(global_ledger, key=lambda x: x['exit_timestamp'])

        portfolio_weights = {"BTCUSDT": 0.40, "ETHUSDT": 0.30, "SOLUSDT": 0.30}
        
        # Define Environment Fee Tier Profiles (fee_bps, slippage_bps, funding_hourly_bps)
        fee_profiles = {
            "Tier 1: Institutional Raw (0.2 bps Fee, 0.5 bps Slip, 0.01 bps Fund)": (0.2, 0.5, 0.01),
            "Tier 2: Retail Standard    (5.0 bps Fee, 2.0 bps Slip, 0.05 bps Fund)": (5.0, 2.0, 0.05),
            "Tier 3: Aggressive Slippage (5.0 bps Fee, 6.0 bps Slip, 0.05 bps Fund)": (5.0, 6.0, 0.05),
            "Tier 4: High Friction Toxic (10.0 bps Fee, 10.0 bps Slip, 0.10 bps Fund)": (10.0, 10.0, 0.10)
        }

        print("\n[STRESS TESTING 2026 OUT-OF-SAMPLE FRONTIER ACROSS MICROSTRUCTURE TIERS]")
        print("------------------------------------------------------------------------------------------")
        
        for name, profile in fee_profiles.items():
            f_bps, s_bps, fund_bps = profile
            res = self.simulate_frictional_timeline(global_ledger, portfolio_weights, f_bps, s_bps, fund_bps, [2026])
            
            pnl = res['final_balance'] - self.initial_balance
            status_tag = "🟢 [SURVIVED]" if res['pf'] >= 1.10 else ("🟡 [BREAKEVEN]" if res['pf'] >= 1.0 else "🔴 [EDGE DESTROYED]")
            
            print(f"▶️ {name}")
            print(f"  ├── Net Profit Factor: {res['pf']:.2f} | Max Drawdown: {res['max_dd']:.1f}% | Net PnL: ${pnl:+,.2f}")
            print(f"  └── Drag Leak Matrix : Commissions: ${res['fees']:.2f} | Slippage: ${res['slippage']:.2f} | Funding Rent: ${res['funding']:.2f} -> {status_tag}\n")
        print("==========================================================================================")

if __name__ == "__main__":
    simulator = ExecutionCostSimulator()
    simulator.run_friction_stress_test()
