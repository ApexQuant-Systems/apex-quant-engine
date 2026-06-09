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

class RegimeEpochMatrixAudit(MultiHorizonTournament):
    """
    Layer 9.98: Institutional Year x Regime Matrix Validation Rig.
    Slices lookahead-insulated transaction ledgers into an explicit 24-cell 
    cross-validation grid to expose hidden edge decay across changing macro horizons.
    """
    def __init__(self, initial_balance=30000.0, max_portfolio_heat=0.06):
        super().__init__(initial_balance, max_portfolio_heat)
        self.years = [2024, 2025, 2026]
        self.regimes = ['BULL_EXPANSION', 'BEAR_EXPANSION']

    def execute_matrix_audit(self):
        print("==========================================================================================")
        print(" 🔍 APEX QUANT OS V3: INSTITUTIONAL YEAR x REGIME CROSS-VALIDATION MATRIX")
        print("==========================================================================================")
        
        for style in self.style_sets:
            style_name = style.replace("SET_", "").replace("_INVESTING", "").replace("_EXPANSION", "")
            print(f"\n🧱 HARDNESS TEST: Corporate Horizon Domain -> {style_name}")
            print(" ----------------------------------------------------------------------------------------")
            print(f" {'EPOCH CORRIDOR':15s} | {'REGIME STATE':16s} | {'TRADES':6s} | {'WIN RATE %':10s} | {'EXPECTANCY (R)':14s} | {'STATUS':10s} |")
            print(" ----------------------------------------------------------------------------------------")
            
            # Compile pristine lookahead-insulated trades for this isolated business unit
            style_ledger = []
            for asset in self.assets:
                try:
                    style_ledger.extend(self.generate_pure_horizon_ledger(asset, style))
                except Exception:
                    continue
                    
            df_style = pd.DataFrame(style_ledger)
            
            if df_style.empty:
                print(f"  🔴 PROFILE FLAT   | Domain generated exactly zero data tracks across historical grid.")
                print(" ----------------------------------------------------------------------------------------")
                continue

            # Walk the explicit Year x Regime grid matrix independently
            for year in self.years:
                for regime in self.regimes:
                    df_cell = df_style[(df_style['year'] == year) & (df_style['regime'] == regime)]
                    cell_label = f"{year}"
                    regime_label = regime.replace("_EXPANSION", "")
                    
                    if df_cell.empty:
                        print(f"  ├── {cell_label:10s} | {regime_label:16s} | {0:6d} | {0.0:9.1f}% | {0.00:14.2f}R | ⚪ HIBERNATE |")
                        continue
                        
                    t_count = len(df_cell)
                    r_multiples = df_cell['risk_mult'].to_numpy()
                    wr = (len(df_cell[df_cell['risk_mult'] > 0]) / t_count) * 100
                    expectancy = np.mean(r_multiples)
                    
                    # Core institutional pass criteria per matrix cell
                    if expectancy >= 0.05:
                        status = "🟢 PERSISTS"
                    elif expectancy > -0.05:
                        status = "🟡 NEUTRAL"
                    else:
                        status = "🔴 DECAYED"
                        
                    print(f"  ├── {cell_label:10s} | {regime_label:16s} | {t_count:6d} | {wr:9.1f}% | {expectancy:+13.2f}R | {status:10s} |")
            print(" ----------------------------------------------------------------------------------------")

if __name__ == "__main__":
    audit = RegimeEpochMatrixAudit()
    audit.execute_matrix_audit()
