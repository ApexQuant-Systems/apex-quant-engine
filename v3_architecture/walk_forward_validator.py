import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from v3_architecture.multi_horizon_tournament import MultiHorizonTournament

class WalkForwardValidator(MultiHorizonTournament):
    """
    Layer 9.99: Clean Out-of-Sample Walk-Forward Validation Core.
    Strictly isolates 2024-2025 as the In-Sample (IS) training period, and 
    uses 2026 as an untouched, completely blind Out-of-Sample (OOS) testing block.
    """
    def __init__(self, initial_balance=30000.0, max_portfolio_heat=0.06):
        super().__init__(initial_balance, max_portfolio_heat)

    def execute_walk_forward_audit(self):
        print("==========================================================================================")
        print(" 🏛️ APEX QUANT OS V3: CLOSED WALK-FORWARD VALIDATION TOURNAMENT")
        print("==========================================================================================")
        print(f" [TRAIN TIMELINE (IN-SAMPLE)]      : 2024 + 2025")
        print(f" [TEST TIMELINE (OUT-OF-SAMPLE)]   : 2026 (Completely Blind Gate)")
        print("==========================================================================================")
        
        wf_rows = []

        for style in self.style_sets:
            style_label = style.replace("SET_", "").replace("_INVESTING", "").replace("_EXPANSION", "")
            
            # Compile pristine lookahead-insulated transaction ledgers
            style_ledger = []
            for asset in self.assets:
                try:
                    style_ledger.extend(self.generate_pure_horizon_ledger(asset, style))
                except Exception:
                    continue
                    
            df_style = pd.DataFrame(style_ledger)
            if df_style.empty or 'year' not in df_style.columns:
                continue

            # 1. Segment the In-Sample (IS) Training Block
            df_is = df_style[df_style['year'].isin([2024, 2025])]
            # 2. Segment the Blind Out-of-Sample (OOS) Test Block
            df_oos = df_style[df_style['year'] == 2026]

            # Calculate In-Sample Performance Metrics
            is_trades = len(df_is)
            is_exp = df_is['risk_mult'].mean() if is_trades > 0 else 0.0
            is_wr = (len(df_is[df_is['risk_mult'] > 0]) / is_trades * 100) if is_trades > 0 else 0.0
            
            # Calculate Out-of-Sample Performance Metrics
            oos_trades = len(df_oos)
            oos_exp = df_oos['risk_mult'].mean() if oos_trades > 0 else 0.0
            oos_wr = (len(df_oos[df_oos['risk_mult'] > 0]) / oos_trades * 100) if oos_trades > 0 else 0.0

            # Compute the structural decay profile ratio
            decay_ratio = oos_exp / is_exp if is_exp > 0 else 0.0
            
            if oos_exp >= 0.05 and decay_ratio >= 0.50:
                verdict = "🟢 PASSED (EDGE VALIDATED)"
            elif oos_exp > 0.0:
                verdict = "🟡 DECAYED (REDUCED EDGE)"
            else:
                verdict = "🔴 FAILED (CURVE-FITTED BLINDSPOT)"

            wf_rows.append({
                'Horizon Playbook': style_label,
                'IS Trades': is_trades,
                'IS WR %': round(is_wr, 1),
                'IS Expect': round(is_exp, 2),
                'OOS Trades': oos_trades,
                'OOS WR %': round(oos_wr, 1),
                'OOS Expect': round(oos_exp, 2),
                'Decay Ratio': round(decay_ratio, 2),
                'Tournament Verdict': verdict
            })

        df_wf_leaderboard = pd.DataFrame(wf_rows)
        print(df_wf_leaderboard.to_string(index=False))
        print("==========================================================================================")

if __name__ == "__main__":
    validator = WalkForwardValidator()
    validator.execute_walk_forward_audit()
