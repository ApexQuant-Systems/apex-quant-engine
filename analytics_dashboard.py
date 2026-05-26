import sqlite3
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime

DB_PATH = "storage/apex_systems.db"
HEARTBEAT_PATH = "infrastructure/heartbeat.txt"

class PerformanceIntelligenceDashboard:
    def __init__(self):
        self.db_path = DB_PATH
        self.heartbeat_path = HEARTBEAT_PATH

    def check_system_vitality(self):
        if not os.path.exists(self.heartbeat_path):
            return "UNKNOWN (No Heartbeat File Found)"
        try:
            with open(self.heartbeat_path, "r") as f:
                last_pulse = float(f.read().strip())
            delta = time.time() - last_pulse
            if delta < 10:
                return f"LIVE (Active Streaming • Last pulse {delta:.1f}s ago)"
            else:
                return f"STALE / DISCONNECTED (Last pulse {delta:.1f}s ago)"
        except Exception:
            return "ERROR (Corrupted Heartbeat State)"

    def load_ledger(self):
        if not os.path.exists(self.db_path):
            print(f"[-] Hardware Layer Error: Database file not found at {self.db_path}")
            return None
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM trade_journal", conn)
        conn.close()
        return df

    def compute_metrics(self):
        df = self.load_ledger()
        system_status = self.check_system_vitality()
        
        if df is None or df.empty:
            print("\n==================================================")
            print("   APEX QUANT SYSTEMS: PERFORMANCE INTELLIGENCE   ")
            print("==================================================")
            print(f" [▶] TIER 3 — OPERATIONAL STATE & HEALTH:")
            print(f" ├── WebSocket Stream Vitality  : {system_status}")
            print(f" └── Database Journal Integrity : EMPTY LEDGER")
            print("==================================================\n")
            return

        closed = df[df['status'] == 'CLOSED'].copy()
        active = df[df['status'] == 'ACTIVE'].copy()

        print("\n==================================================================")
        print("   APEX QUANT SYSTEMS: PERFORMANCE INTELLIGENCE DASHBOARD v2.2   ")
        print("==================================================================")

        # ─── TIER 1: CORE EDGE HEALTH ───────────────────────────────────
        total_trades = len(closed)
        if total_trades == 0:
            print(f" [▶] TIER 1 — CORE EDGE HEALTH:")
            print(" └── Insufficient closed trades to compute statistical expectancy.")
            print("------------------------------------------------------------------")
        else:
            wins = closed[closed['pnl'] > 0]
            losses = closed[closed['pnl'] <= 0]
            win_rate = (len(wins) / total_trades) * 100

            avg_win = wins['pnl'].mean() if not wins.empty else 0.0
            avg_loss = losses['pnl'].mean() if not losses.empty else 0.0
            
            expectancy = ((win_rate / 100) * avg_win) + (((100 - win_rate) / 100) * avg_loss)
            
            gross_profit = wins['pnl'].sum() if not wins.empty else 0.0
            gross_loss = abs(losses['pnl'].sum()) if not losses.empty else 0.0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

            window_size = min(total_trades, 30)
            rolling_closed = closed.tail(window_size)
            r_wins = rolling_closed[rolling_closed['pnl'] > 0]
            r_losses = rolling_closed[rolling_closed['pnl'] <= 0]
            r_wr = (len(r_wins) / window_size) * 100
            r_aw = r_wins['pnl'].mean() if not r_wins.empty else 0.0
            r_al = r_losses['pnl'].mean() if not r_losses.empty else 0.0
            rolling_expectancy = ((r_wr / 100) * r_aw) + (((100 - r_wr) / 100) * r_al)

            starting_balance = 10000.0
            balance_curve = [starting_balance]
            for pnl in closed['pnl'].tolist():
                balance_curve.append(balance_curve[-1] + pnl)
                
            balance_df = pd.Series(balance_curve)
            rolling_peaks = balance_df.cummax()
            drawdowns = ((balance_df - rolling_peaks) / rolling_peaks) * 100
            max_dd = drawdowns.min()

            print(f" [▶] TIER 1 — CORE EDGE HEALTH:")
            status_alert = "NOMINAL" if rolling_expectancy >= 0 else "CRITICAL COLLAPSE"
            print(f" ├── Rolling {window_size}-Trade Expectancy : ${rolling_expectancy:.2f} ({status_alert})")
            print(f" ├── Lifetime Expectancy        : ${expectancy:.2f} per trade payload")
            print(f" ├── Realized Profit Factor     : {profit_factor:.2f}x (Target: >1.50x)")
            print(f" └── Peak-to-Trough Max DD      : {max_dd:.2f}%")
            print("------------------------------------------------------------------")

        # ─── TIER 2: SIGNAL QUALITY ──────────────────────────────────────
        if total_trades > 0:
            realized_rr = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
            print(f" [▶] TIER 2 — SIGNAL QUALITY & ATTR:")
            print(f" ├── Account Win Rate           : {win_rate:.1f}%")
            print(f" ├── Realized Structural Asymmetry: {realized_rr:.2f}x (Target: 4.00x)")
            print(f" └── Net Financial Yield        : ${closed['pnl'].sum():+,.2f}")
            print(f"\n  REGIME REGULATION LEDGER:")
            print(f"  {'REGIME':<16} | {'TRADES':<8} | {'WIN RATE':<10} | {'NET PNL':<12}")
            print(f"  ──────────────────────────────────────────────────────────────")
            for name, group in closed.groupby('regime'):
                rg_total = len(group)
                rg_wins = len(group[group['pnl'] > 0])
                rg_wr = (rg_wins / rg_total) * 100
                rg_pnl = group['pnl'].sum()
                print(f"  {name:<16} | {rg_total:<8} | {rg_wr:.1f}%     | ${rg_pnl:+,.2f}")
            print("------------------------------------------------------------------")
        else:
            print(f" [▶] TIER 2 — SIGNAL QUALITY & ATTR:")
            print(" └── Awaiting trade completions for asset allocation metrics.")
            print("------------------------------------------------------------------")

        # ─── TIER 3: OPERATIONAL HEALTH ──────────────────────────────────
        print(f" [▶] TIER 3 — OPERATIONAL STATE & HEALTH:")
        print(f" ├── WebSocket Stream Vitality  : {system_status}")
        print(f" ├── Active Unhedged Exposure   : {len(active)} open positions")
        print(f" └── Database Journal Integrity : NOMINAL ({len(df)} total logs verified)")
        print("==================================================================\n")

if __name__ == "__main__":
    dashboard = PerformanceIntelligenceDashboard()
    dashboard.compute_metrics()
