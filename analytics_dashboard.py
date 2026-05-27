import sqlite3
import os
import sys
from pathlib import Path

DB_PATH = Path("./storage/apex_systems.db")

def execute_high_fidelity_audit():
    if not DB_PATH.exists():
        print(f"[🛑 ERROR] Database missing at {DB_PATH}. Run your unchained backtest first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='closed_trades';")
        if not cursor.fetchone():
            print("[⚠️ EMPTY Ledger] Table 'closed_trades' does not exist yet. Let the unchained backtest finish.")
            return

        cursor.execute("SELECT COUNT(*) FROM closed_trades")
        total_trades = cursor.fetchone()[0]
        if total_trades == 0:
            print("[⚠️ EMPTY STATUS] No realized trade lifecycles logged on disk yet.")
            return

        print("=====================================================================")
        print("        APEX QUANT SYSTEMS — QUANTITATIVE EXPECTANCY LAB            ")
        print("=====================================================================")
        print(f"[*] Extracting behavioral metrics from {total_trades} unchained trade records...\n")

        # --- High-Fidelity Performance Metrics ---
        cursor.execute("SELECT COUNT(*) FROM closed_trades WHERE pnl_percent > 0")
        wins = cursor.fetchone()[0]
        losses = total_trades - wins
        win_rate = (wins / total_trades) * 100

        cursor.execute("SELECT AVG(pnl_percent) FROM closed_trades WHERE pnl_percent > 0")
        avg_win = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT AVG(pnl_percent) FROM closed_trades WHERE pnl_percent <= 0")
        avg_loss = abs(cursor.fetchone()[0] or 0.0)

        # Compute formal Mathematical Expectancy
        expectancy = ((win_rate / 100.0) * avg_win) - ((1.0 - (win_rate / 100.0)) * avg_loss)

        cursor.execute("SELECT SUM(pnl_percent) FROM closed_trades WHERE pnl_percent > 0")
        gross_profit = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(pnl_percent) FROM closed_trades WHERE pnl_percent <= 0")
        gross_loss = abs(cursor.fetchone()[0] or 0.0)
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        print("[🏆 GLOBAL SYSTEM EDGE FOOTPRINT]")
        print(f"  -> Total Positions Evaluated : {total_trades} Mapped Trades")
        print(f"  -> Realized Core Win Rate    : {win_rate:.2f}%  [Wins: {wins} | Losses: {losses}]")
        print(f"  -> Asymmetric Yield Ratio   : Avg Win: +{avg_win:.2f}% | Avg Loss: -{avg_loss:.2f}%")
        print(f"  -> Mathematical Expectancy   : {expectancy:.4f}% per trade entry")
        print(f"  -> Gross Profit Factor       : {profit_factor:.4f}")
        
        # --- Cross-Asset Expectancy Matrix ---
        print("\n[📊 TOKEN SPECIFIC METRIC CORES]")
        cursor.execute("""
            SELECT symbol, COUNT(*),
                   SUM(CASE WHEN pnl_percent > 0 THEN 1 ELSE 0 END),
                   AVG(CASE WHEN pnl_percent > 0 THEN pnl_percent ELSE NULL END),
                   AVG(CASE WHEN pnl_percent <= 0 THEN pnl_percent ELSE NULL END)
            FROM closed_trades GROUP BY symbol
        """)
        print(f"{'Token Asset':<12} | {'Trades':<8} | {'Win Rate':<10} | {'Avg Win %':<11} | {'Avg Loss %'}")
        print("-" * 62)
        for row in cursor.fetchall():
            sym, t_cnt, w_cnt, a_w, a_l = row
            a_w = a_w or 0.0
            a_l = abs(a_l or 0.0)
            a_wr = (w_cnt / t_cnt) * 100 if t_cnt > 0 else 0
            print(f"{sym:<12} | {t_cnt:<8} | {a_wr:.1f}%     | +{a_w:.2f}%     | -{a_l:.2f}%")

        # --- Regime Optimization Localization ---
        print("\n[🧠 REGIME PERFORMANCE LOCALIZATION]")
        cursor.execute("""
            SELECT regime, COUNT(*), AVG(pnl_percent),
                   SUM(CASE WHEN pnl_percent > 0 THEN pnl_percent ELSE 0 END) / 
                   NULLIF(SUM(CASE WHEN pnl_percent <= 0 THEN ABS(pnl_percent) ELSE 0 END), 0)
            FROM closed_trades GROUP BY regime
        """)
        print(f"{'Market Regime Profile':<25} | {'Sample Trades':<15} | {'Net Return':<12} | {'Profit Factor'}")
        print("-" * 72)
        for row in cursor.fetchall():
            reg, cnt, net_r, pf = row
            pf_str = f"{pf:.2f}" if pf is not None else "INF"
            print(f"{reg:<25} | {cnt:<15} | {net_r:+.4f}%   | {pf_str}")
            
        print("=====================================================================\n")

    except Exception as e:
        print(f"[🛑 DASHBOARD CRASH] Failed to extract performance dataset: {e}", file=sys.stderr)
    finally:
        conn.close()

if __name__ == "__main__":
    execute_high_fidelity_audit()
