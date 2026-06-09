import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from v2_architecture.portfolio_event_engine import PortfolioEventEngine

class FactorRiskEngine(PortfolioEventEngine):
    """
    Layer 9.7: Sovereign Factor Risk & Attenuated Firewall Engine.
    Consolidates concurrent token signals into a single 'Crypto Beta' factor bucket,
    and enforces a defensive risk floor to eliminate asymmetric win suffocation.
    """
    def __init__(self, initial_balance=30000.0, max_portfolio_heat=0.06):
        super().__init__(initial_balance, max_portfolio_heat)

    def execute_factor_aware_simulation(self, global_ledger, target_years):
        balance = self.initial_balance
        peak = balance
        max_dd = 0.0
        
        wins, losses = 0, 0
        total_pnl_won, total_pnl_lost = 0.0, 0.0
        active_positions = []
        
        df_ledger = pd.DataFrame(global_ledger)
        df_ledger = df_ledger[df_ledger['year'].isin(target_years)]
        
        if df_ledger.empty:
            return 0, 0.0, 0.0, balance, 0.0

        # Enforce unified chronological timelines across all cartridges
        unified_timeline = sorted(list(set(df_ledger['entry_timestamp'].tolist() + df_ledger['exit_timestamp'].tolist())))

        for current_tick in unified_timeline:
            still_active = []
            
            # PHASE 1: CHRONOLOGICAL POSITION EXIT PROCESSING
            for pos in active_positions:
                if current_tick >= pos['exit_timestamp']:
                    trade_pnl = pos['allocated_risk_capital'] * pos['risk_mult']
                    balance += trade_pnl
                    
                    if trade_pnl > 0:
                        wins += 1; total_pnl_won += trade_pnl
                    else:
                        losses += 1; total_pnl_lost += abs(trade_pnl)
                else:
                    still_active.append(pos)
            active_positions = still_active

            if balance > peak: peak = balance
            current_dd = (peak - balance) / peak
            if current_dd > max_dd: max_dd = current_dd

            # PHASE 2: INCOMING CONCURRENT SIGNAL INTERCEPTION
            concurrent_signals = df_ledger[df_ledger['entry_timestamp'] == current_tick].to_dict('records')
            if not concurrent_signals: continue

            # PHASE 3: ATTENUATED DRAWDOWN FIREWALL MATRIX (STAGE 2)
            # Implements a structural protective floor at x0.25 to prevent win suffocation
            if current_dd >= 0.20: risk_scale = 0.2500    # Defends capital but keeps recovery math intact
            elif current_dd >= 0.15: risk_scale = 0.5000  # Attenuated intermediate tier
            elif current_dd >= 0.10: risk_scale = 0.7500  # Soft defensive drop
            else: risk_scale = 1.0000                     # Standard baseline allocation

            # PHASE 4: THE CRYPTO BETA FACTOR BUCKET HARD CAP (STAGE 1 & 3)
            # Hard-caps the total allocation of concurrent signals to a shared 1.0% risk block
            factor_bucket_cap = 0.0100 
            total_allocated_factor_risk = 0.0
            
            scored_candidates = []
            for sig in concurrent_signals:
                base_conf = self.cartridge_confidence.get(sig['asset'], 50)
                priority_score = base_conf * sig['computed_rr']
                scored_candidates.append({**sig, 'priority_score': priority_score})
            scored_candidates = sorted(scored_candidates, key=lambda x: x['priority_score'], reverse=True)

            for candidate in scored_candidates:
                # If the shared factor bucket for this candle window is saturated, skip lower-ranked signals
                if total_allocated_factor_risk >= factor_bucket_cap: 
                    break

                # Slice remaining capacity inside the 1% Factor Bucket
                remaining_factor_capacity = factor_bucket_cap - total_allocated_factor_risk
                target_allocation_slot = 0.01 / len(scored_candidates) # Equal division across the cluster
                
                allocated_risk = min(target_allocation_slot, remaining_factor_capacity)
                final_risk_pct = allocated_risk * risk_scale

                if final_risk_pct <= 0: continue

                candidate['risk_budget_pct'] = final_risk_pct
                candidate['allocated_risk_capital'] = balance * final_risk_pct
                
                active_positions.append(candidate)
                total_allocated_factor_risk += allocated_risk

        total_trades = wins + losses
        net_pf = total_pnl_won / total_pnl_lost if total_pnl_lost > 0 else total_pnl_won
        recovery_factor = (balance - self.initial_balance) / (self.initial_balance * max_dd + 1e-8)
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0.0
        
        return total_trades, win_rate, net_pf, max_dd * 100, balance, recovery_factor

    def run_factor_tournament(self):
        print("==========================================================================================")
        print(" 🏛️ APEX QUANT OS CORE: FACTOR RISK LAYER & ATTENUATED FIREWALL SUITE")
        print("==========================================================================================")
        
        global_ledger = []
        for asset in self.assets:
            trades = self.extract_cartridge_trades(asset)
            global_ledger.extend(trades)
        global_ledger = sorted(global_ledger, key=lambda x: x['entry_timestamp'])

        print("\n[STRESS TESTING INTEGRATED MECHANISMS OVER UN-BLINDED 2026 OUT-OF-SAMPLE FRONTIER]")
        print("------------------------------------------------------------------------------------------")
        
        # 1. Run the old suffocating discrete event track as the control benchmark
        t_tr, t_wr, t_pf, t_dd, t_bal, t_rf = self.execute_event_driven_simulation(global_ledger, [2026])
        
        # 2. Run the new Factor-Aware Attenuated Engine
        f_tr, f_wr, f_pf, f_dd, f_bal, f_rf = self.execute_factor_aware_simulation(global_ledger, [2026])
        
        print(f"▶️ SUFFOCATING DISCRETE ENGINE (CONTROL BENCHMARK):")
        print(f"  ├── Executed Trades  : {t_tr} Trades | Win Rate: {t_wr:.1f}%")
        print(f"  └── Net Profit Factor: {t_pf:.2f} | Max Drawdown: {t_dd:.1f}% | Recovery Factor: {t_rf:.2f}")
        print(f"")
        print(f"▶️🔒 FACTOR-AWARE ENGINE (ATTENUATED CORE FLOOR):")
        print(f"  ├── Executed Trades  : {f_tr} Trades | Win Rate: {f_wr:.1f}%")
        print(f"  └── Net Profit Factor: {f_pf:.2f} | Max Drawdown: {f_dd:.1f}% | Recovery Factor: {f_rf:.2f}")
        print("==========================================================================================")

if __name__ == "__main__":
    engine = FactorRiskEngine()
    engine.run_factor_tournament()
