import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from v3_architecture.trade_attribution_analyzer import TradeAttributionAnalyzer

class RobustnessTestingSuite(TradeAttributionAnalyzer):
    """
    Layer 9.95: Advanced Institutional Stress & Robustness Rig.
    Subjecting lookahead-insulated strategy sets to Slippage Degradation, 
    10,000-run Monte Carlo simulations, Tail-Risk run downs, and pure 
    Regime Isolation paths.
    """
    def __init__(self, initial_balance=30000.0, max_portfolio_heat=0.06):
        super().__init__(initial_balance, max_portfolio_heat)

    def run_robustness_testing(self, target_years=[2024, 2025, 2026]):
        print("==========================================================================================")
        print(" 🚨 APEX QUANT OS V3: INSTITUTIONAL ROBUSTNESS & DEGRADATION RIG")
        print("==========================================================================================")
        
        target_styles = ["SET_3_SHORT_TERM_SWING", "SET_4_INTRADAY_EXPANSION"]
        
        # Phase 1: Compile lookahead-insulated transaction ledgers
        raw_ledger = []
        for style in target_styles:
            for asset in self.assets:
                trades = self.extract_audited_style_ledger(asset, style, apply_lookahead_deflector=True)
                raw_ledger.extend(trades)
                
        df_base = pd.DataFrame(raw_ledger)
        if df_base.empty:
            print("🔴 [CRITICAL] Empty base transaction array. Aborting robustness simulation.")
            return
            
        df_base = df_base[df_base['year'].isin(target_years)].sort_values('entry_timestamp')
        
        # Re-run base timeline validation to collect pristine realized R-multiples
        executed_r_multiples = []
        regimes_list = []
        styles_list = []
        
        active_positions = []
        unified_timeline = sorted(list(set(df_base['entry_timestamp'].tolist() + df_base['exit_timestamp'].tolist())))

        for current_tick in unified_timeline:
            still_active = []
            for pos in active_positions:
                if current_tick >= pos['exit_timestamp']:
                    executed_r_multiples.append(pos['risk_mult'])
                    regimes_list.append(pos['regime'])
                    styles_list.append(pos['style'])
                else:
                    still_active.append(pos)
            active_positions = still_active

            concurrent_signals = df_base[df_base['entry_timestamp'] == current_tick].to_dict('records')
            for sig in concurrent_signals:
                active_positions.append(sig)

        r_arr = np.array(executed_r_multiples)
        total_trades = len(r_arr)
        
        print(f"[*] Lookahead-Insulated Base Trades Compiled: {total_trades} Loaded Transactions.")
        print(f"[*] Base System Expectancy Value             : +{np.mean(r_arr):.2f} R-Units")
        
        # --- AUDIT 1: TRANSACTIONS COST / SLIPPAGE DEGRADATION PASS ---
        print("\n[AUDIT 1: EXPERIMENTAL SLIPPAGE DEGRADATION SPECTRUM]")
        print("------------------------------------------------------------------------------------------")
        print(f" {'SLIPPAGE LEVEL (DRAG)':25s} | {'DEGRADED EXPECTANCY':22s} | {'SYSTEM STATUS':15s} |")
        print("------------------------------------------------------------------------------------------")
        
        slippage_tiers = {
            "0.05% Price Slip (-0.05R)": 0.05,
            "0.10% Price Slip (-0.10R)": 0.10,
            "0.20% Price Slip (-0.20R)": 0.20,
            "0.30% Heavy Drag  (-0.30R)": 0.30
        }
        
        for name, drag in slippage_tiers.items():
            degraded_expectancy = np.mean(r_arr - drag)
            status = "🟢 SURVIVES" if degraded_expectancy > 0.05 else "🔴 CRITICAL FAILURE"
            print(f"  ├── {name:22s} | +{degraded_expectancy:.3f} R-Units Per Trade | {status:15s} |")

        # --- AUDIT 2: MONTE CARLO BOOTSTRAP ENGINE (10,000 SIMULATIONS) ---
        print("\n[AUDIT 2: MONTE CARLO SIMULATION CORE - 10,000 CHRONOLOGICAL SHUFFLES]")
        print("------------------------------------------------------------------------------------------")
        iterations = 10000
        mc_terminal_returns = []
        
        # Seed engine for absolute verification metrics consistency
        np.random.seed(42)
        for _ in range(iterations):
            # Bootstrap shuffle the historical return stream to randomize gaps and execution sequence
            bootstrapped_sample = np.random.choice(r_arr, size=total_trades, replace=True)
            # Calculate total return multiplier assuming a fixed 1% account size deployment slot
            terminal_pnl_pct = np.sum(bootstrapped_sample * 0.01) * 100
            mc_terminal_returns.append(terminal_pnl_pct)
            
        mc_terminal_returns = np.array(mc_terminal_returns)
        
        # Compute exact institutional confidence interval metrics
        p5_bound = np.percentile(mc_terminal_returns, 5)
        p50_bound = np.percentile(mc_terminal_returns, 50)
        p95_bound = np.percentile(mc_terminal_returns, 95)
        probability_of_ruin = (np.sum(mc_terminal_returns < 0) / iterations) * 100

        print(f"  ├── 95th Percentile Outcome (Optimistic Case) : {p95_bound:+.1f}% Equity Growth")
        print(f"  ├── 50th Percentile Outcome (Median Performance): {p50_bound:+.1f}% Equity Growth")
        print(f"  ├── 5th Percentile Outcome  (Worst-Case Bounds) : {p55_bound:+.1f}% Equity Growth" if 'p55_bound' in locals() else f"  ├── 5th Percentile Outcome  (Worst-Case Bounds) : {p5_bound:+.1f}% Equity Growth")
        print(f"  └── Mathematical Probability of Capital Loss    : {probability_of_ruin:.3f}% (Institutional Pass Gate < 1%)")

        # --- AUDIT 5: TAIL RISK CONSECUTIVE LOSS STRIP DRAWDOWN MATRIX ---
        print("\n[AUDIT 5: CENTRAL FIREWALL TAIL-RISK RUN DOWN MATRIX]")
        print("------------------------------------------------------------------------------------------")
        print(f" {'CONSECUTIVE LOSS STREAK':25s} | {'REALIZED R-LOSS SIZE':22s} | {'PORTFOLIO RETURN DRAG':22s} |")
        print("------------------------------------------------------------------------------------------")
        
        loss_streaks = [5, 8, 10, 15, 20]
        avg_mitigated_loss = np.mean(r_arr[r_arr <= 0])  # ~ -0.54R from attribution logs
        
        for streak in loss_streaks:
            # Compounding impact on account capitalization
            total_r_lost = streak * avg_mitigated_loss
            account_drag_pct = total_r_lost * 1.0  # Assumes baseline 1% sizing multiplier allocation
            print(f"  ├── {streak:2d} Successive Failures   | {total_r_lost:6.2f} Total R-Units   | {account_drag_pct:+.2f}% Gross Equity Hit |")

        # --- REGIME BLINDSPOT VERIFICATION INTERCEPT ---
        print("\n[RE-VERIFYING THE REGIME BLINDSPOT: COLD FACTOR SEGREGATION]")
        print("------------------------------------------------------------------------------------------")
        df_metrics = pd.DataFrame({
            'r': r_arr,
            'regime': regimes_list,
            'style': styles_list
        })
        
        regime_groups = df_metrics.groupby('regime')
        for group_name, df_group in regime_groups:
            g_total = len(df_group)
            g_exp = df_group['r'].mean()
            g_wr = (len(df_group[df_group['r'] > 0]) / g_total) * 100
            
            print(f" ▶️ Structural Category: {group_name:21s} | Volume: {g_total:4d} Trades | WR: {g_wr:5.1f}% | Expectancy: +{g_exp:.2f} R-Units")
        print("==========================================================================================")

if __name__ == "__main__":
    suite = RobustnessTestingSuite()
    suite.run_robustness_testing([2024, 2025, 2026])
