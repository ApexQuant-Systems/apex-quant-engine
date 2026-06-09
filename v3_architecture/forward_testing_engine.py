import os
import sys
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from v3_architecture.multi_horizon_tournament import MultiHorizonTournament

class ForwardTestingEngine(MultiHorizonTournament):
    """
    Apex Quant OS v3.0: Forward Simulation Control Room.
    Acts as the production hub executing frozen strategy scans, logging a
    virtual SQL ledger, tracking execution telemetry, and rendering the 
    Historical vs. Forward Expectancy Matrix.
    """
    def __init__(self, db_path="./data/forward_testing_vault.db"):
        super().__init__(initial_balance=30000.0, max_portfolio_heat=0.06)
        self.db_path = db_path
        self.init_database_infrastructure()
        
        # Frozen Institutional Confidence Tier Allocations
        self.tier_allocations = {
            "SET_1_MACRO_INVESTING": {"tier": "Tier C (Observation)", "weight": 0.05, "hist_exp": 1.37},
            "SET_2_MEDIUM_SWING":    {"tier": "Tier B (Validation)",  "weight": 0.15, "hist_exp": 0.91},
            "SET_3_SHORT_POSITION":  {"tier": "Tier A (Core Fund)",   "weight": 0.40, "hist_exp": 0.51},
            "SET_4_INTRADAY_EXPANSION":{"tier": "Tier A (Core Fund)",   "weight": 0.40, "hist_exp": 0.39}
        }

    def init_database_infrastructure(self):
        """Initializes localized storage vaults for persistent state logging."""
        Path(os.path.dirname(self.db_path)).mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Virtual execution ledger journal table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS virtual_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, asset TEXT, style TEXT, direction TEXT,
                entry_price REAL, sl REAL, tp REAL, computed_rr REAL,
                exit_timestamp TEXT, realized_r REAL, status TEXT
            )
        """)
        conn.commit()
        conn.close()

    def scan_and_journal_forward_signals(self, fake_live_tick_time=None):
        """
        Simulates live WebSocket intercepts by pulling the latest data blocks
        and processing them directly through your frozen structural decision core.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for style in self.style_sets:
            for asset in self.assets:
                try:
                    # Execute lookahead-insulated rule scanning matrix loops
                    raw_trades = self.generate_pure_horizon_ledger(asset, style)
                    if not raw_trades: continue
                    
                    # Intercept the final trade generation index slot to log into the database
                    latest_signal = raw_trades[-1]
                    
                    # Verify if signal already has an open track inside the journal database
                    cursor.execute(
                        "SELECT id FROM virtual_ledger WHERE asset=? AND style=? AND entry_timestamp=?",
                        (asset, style, str(latest_signal['entry_timestamp']))
                    )
                    if cursor.fetchone() is None:
                        # Log fresh structural signal straight into the production database table
                        exit_t = str(latest_signal['exit_timestamp']) if latest_signal['exit_timestamp'] else "OPEN"
                        cursor.execute("""
                            INSERT INTO virtual_ledger 
                            (timestamp, asset, style, direction, entry_price, sl, tp, computed_rr, exit_timestamp, realized_r, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(latest_signal['entry_timestamp']), asset, style, latest_signal['direction'],
                            latest_signal['entry_price'], latest_signal['sl'], latest_signal['tp'],
                            latest_signal['computed_rr'], exit_t, latest_signal['risk_mult'],
                            "CLOSED" if latest_signal['exit_timestamp'] else "ACTIVE"
                        ))
                except Exception:
                    continue
        conn.commit()
        conn.close()

    def render_control_room_dashboard(self):
        """Renders an institutional ASCII execution grid directly onto the shell output frame."""
        conn = sqlite3.connect(self.db_path)
        df_forward = pd.read_sql_query("SELECT * FROM virtual_ledger", conn)
        conn.close()

        os.system('clear' if os.name == 'posix' else 'cls')
        print("==========================================================================================")
        print(" 🛰️ APEX QUANT OS V3.0 : SYSTEM INTEGRITY & FORWARD TELEMETRY HUB")
        print("==========================================================================================")
        print(f" Current Execution Clock : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f" Strategy Status Logic   : 🔒 FROZEN PRODUCTION CONFIGURATION")
        print(f" Local Storage Database  : {self.db_path}")
        print("==========================================================================================")
        
        # Render active signal monitoring layer
        df_active = df_forward[df_forward['status'] == "ACTIVE"]
        print(f" 🟢 ACTIVE MONITORING VIRTUAL POSITIONS : {len(df_active)} Open Tracks")
        print(" ----------------------------------------------------------------------------------------")
        if df_active.empty:
            print("  [No Active Position Slots Engaged. Scanning Price Streams...]")
        else:
            for _, row in df_active.head(5).iterrows():
                print(f"  ├── [{row['style'].replace('SET_', ''):18s}] {row['asset']:9s} {row['direction']:5s} | Entry: {row['entry_price']:10.2f} | SL: {row['sl']:10.2f} | TP: {row['tp']:10.2f} | Initial R: {row['computed_rr']:.1f}R")
        
        print("\n==========================================================================================")
        print(" 📊 SYSTEM SPECTRA MATRIX: HISTORICAL BENCHMARK vs. FORWARD EXPECTANCY LIVE")
        print("==========================================================================================")
        print(f" {'HORIZON BUSINESS STRATEGY':24s} | {'CONFIDENCE TIER':22s} | {'ALLOC':5s} | {'HIST R':8s} | {'FWD TRADES':10s} | {'FWD R EXPECT':12s} |")
        print(" ----------------------------------------------------------------------------------------")
        
        for style, meta in self.tier_allocations.items():
            df_style_fwd = df_forward[(df_forward['style'] == style) & (df_forward['status'] == "CLOSED")]
            fwd_count = len(df_style_fwd)
            fwd_expectancy = df_style_fwd['realized_r'].mean() if fwd_count > 0 else 0.0
            
            clean_name = style.replace("SET_", "").replace("_INVESTING", "").replace("_EXPANSION", "")
            alloc_pct = f"{meta['weight']*100:2.0f}%"
            
            print(f" ├── {clean_name:20s} | {meta['tier']:22s} | {alloc_pct:5s} | +{meta['hist_exp']:.2f}R  | {fwd_count:10d} | +{fwd_expectancy:10.2f}R |")
            
        print("==========================================================================================")
        
        # Calculate systemic portfolio metrics summary parameters
        df_closed = df_forward[df_forward['status'] == "CLOSED"]
        if not df_closed.empty:
            total_fwd_ops = len(df_closed)
            fwd_wr = (len(df_closed[df_closed['realized_r'] > 0]) / total_fwd_ops) * 100
            global_fwd_expectancy = df_closed['realized_r'].mean()
            print(f" ▶️ INTEGRATED FUND TELEMETRY -> Closed Ops: {total_fwd_ops} | Forward WR: {fwd_wr:.1f}% | Live Expected Value: +{global_fwd_expectancy:.2f} R-Units")
            print("==========================================================================================")

if __name__ == "__main__":
    control_room = ForwardTestingEngine()
    # Execute step scan to build database tracking layers
    print("[*] Synchronizing forward data stream pipelines...")
    control_room.scan_and_journal_forward_signals()
    # Output dashboard rendering interface
    control_room.render_control_room_dashboard()
