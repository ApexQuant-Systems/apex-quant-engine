import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from v3_architecture.hierarchical_decision_engine import HierarchicalDecisionEngine

class MasterTournamentDirector(HierarchicalDecisionEngine):
    """
    Apex Quant OS v3: Master Tournament Director.
    Evaluates 12 distinct multi-horizon style candidates (4 Styles x 3 Assets) 
    in absolute isolation, generates un-biased production scorecards, 
    and isolates the ultimate surviving alpha combinations.
    """
    def __init__(self, initial_balance=30000.0, max_portfolio_heat=0.06):
        super().__init__(initial_balance, max_portfolio_heat)
        self.styles = [
            "SET_1_LONG_TERM_INVESTING",
            "SET_2_INTERMEDIATE_SWING",
            "SET_3_SHORT_TERM_SWING",
            "SET_4_INTRADAY_EXPANSION"
        ]

    def execute_style_tournament(self, target_year=[2026]):
        print("==========================================================================================")
        print(" 🏆 WELCOME TO THE APEX QUANT OS V3 SYSTEMIC ALPHAS TOURNAMENT")
        print("==========================================================================================")
        
        scorecard_rows = []
        surviving_ledger = []
        
        for style in self.styles:
            print(f"\n[*] Processing Isolated Playbook Arena: {style}")
            print(" ----------------------------------------------------------------------------------------")
            
            for asset in self.assets:
                try:
                    raw_trades = self.compute_pure_style_ledger(asset, style)
                    df_trades = pd.DataFrame(raw_trades)
                    
                    if df_trades.empty:
                        scorecard_rows.append({
                            'Style': style, 'Asset': asset, 'Trades': 0, 'WinRate %': 0.0,
                            'Net PF': 0.0, 'Max DD %': 0.0, 'Recovery': 0.0, 'Status': '🔴 TERMINATED (NO TRADES)'
                        })
                        continue
                        
                    style_asset_trades = df_trades[df_trades['year'].isin(target_year)].to_dict('records')
                    t_count, wr, pf, dd, bal, rf = self.execute_event_driven_simulation(style_asset_trades, target_year)
                    
                    is_survivor = pf >= 1.05 and rf > 0
                    status_tag = "🟢 PASSED TO SECTOR FUND" if is_survivor else "🔴 ELIMINATED (SUB-HERD EXPECTANCY)"
                    
                    if is_survivor:
                        surviving_ledger.extend(style_asset_trades)

                    scorecard_rows.append({
                        'Style': style.replace("SET_", ""),
                        'Asset': asset,
                        'Trades': t_count,
                        'WinRate %': round(wr, 1),
                        'Net PF': round(pf, 2),
                        'Max DD %': round(dd, 1),
                        'Recovery': round(rf, 2),
                        'Status': status_tag
                    })
                    print(f"  ├── {asset:9s} -> Trades: {t_count:3d} | Net PF: {pf:.2f} | Max DD: {dd:4.1f}% -> {status_tag}")
                    
                except Exception as e:
                    print(f"  └── [CRITICAL ERROR] Failed tournament initialization on {asset}-{style}: {e}")

        df_scorecard = pd.DataFrame(scorecard_rows)
        print("\n==========================================================================================")
        print(" 📊 UN-BIASED PRODUCTION STYLE SCORECARD LEADERBOARD (2026 OUT-OF-SAMPLE)")
        print("==========================================================================================")
        print(df_scorecard.to_string(index=False))
        print("==========================================================================================")

        print("\n[PHASE 3: COMBINED CORE FUND INTEGRATION RUN (SURVIVING ALPHA CARTRIDGES)]")
        print("------------------------------------------------------------------------------------------")
        
        if len(surviving_ledger) == 0:
            print(" 🔴 SYSTEMIC TOURNAMENT FAILURE: No style candidates survived the out-of-sample hurdle constraints.")
            print("==========================================================================================")
            return

        surviving_ledger = sorted(surviving_ledger, key=lambda x: x['entry_timestamp'])
        gt, gwr, gpf, gdd, gbal, grf = self.execute_event_driven_simulation(surviving_ledger, target_year)
        pnl = gbal - self.initial_balance
        
        print(f" Total Surviving Candidates Pooled : {df_scorecard['Status'].str.contains('🟢').sum()} Alpha Slots Active")
        print(f" Total Combined Operations Executed: {gt} Combined Trades")
        print(f" Integrated Portfolio Win Rate      : {gwr:.1f}%")
        print(f" Integrated Net Fund Profit Factor : {gpf:.2f} 🚀")
        print(f" Integrated Maximum Fund Drawdown  : {gdd:.1f}% 🛡️")
        print(f" Integrated Final Portfolio Return : ${pnl:+,.2f} (Account Balance: ${gbal:,.2f})")
        print(f" Integrated System Recovery Factor : {grf:.2f}")
        print("==========================================================================================")

if __name__ == "__main__":
    director = MasterTournamentDirector()
    director.execute_style_tournament([2026])
