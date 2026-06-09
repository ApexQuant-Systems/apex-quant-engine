import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

class LiveStateProcessor:
    """
    Apex Quant OS v3.0: State-Driven Production Processing Engine.
    Eliminates global historical data-peeking. Evaluates incoming stream data 
    candle-by-candle and manages live virtual execution states natively.
    """
    def __init__(self, db_path="./data/forward_testing_vault.db"):
        self.db_path = db_path
        self.assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self.init_clean_vault()
        
    def init_clean_vault(self):
        Path(os.path.dirname(self.db_path)).mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Ensure our production schema logs every tracking variable explicitly
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS live_book (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT, style TEXT, direction TEXT,
                entry_time TEXT, entry_price REAL, sl REAL, tp REAL,
                current_sl REAL, exit_time TEXT, realized_r REAL, status TEXT
            )
        """)
        conn.commit()
        conn.close()

    def process_live_candle_tick(self, asset, style, htf_row, mtf_row, ltf_row):
        """
        Core Streaming Selector. Processes a single isolated slice of incoming data.
        Tracks active tracking parameters inside the live database ledger.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if this asset-style configuration currently holds an active open market slot
        cursor.execute(
            "SELECT id, entry_price, sl, current_sl, tp FROM live_book WHERE asset=? AND style=? AND status='ACTIVE'",
            (asset, style)
        )
        active_trade = cursor.fetchone()
        
        current_time_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        if active_trade:
            trade_id, entry_p, base_sl, current_sl, take_profit = active_trade
            ltf_close = ltf_row['close']
            ltf_low = ltf_row['low']
            ltf_high = ltf_row['high']
            mtf_trail = mtf_row['ema_fast'] # MTF 20 EMA handles trailing stop protection natively

            # 1. Evaluate Terminal Stop-Loss Breach
            if ltf_low <= current_sl:
                cursor.execute(
                    "UPDATE live_book SET exit_time=?, realized_r=-1.0, status='CLOSED' WHERE id=?",
                    (current_time_str, trade_id)
                )
                print(f"  🛑 [EXIT ALERT] {asset} {style} hit Stop-Loss at {current_sl}. Realized: -1.00R")
                
            # 2. Evaluate Maximum Macro Take-Profit Target Breach
            elif ltf_high >= take_profit:
                risk_dist = abs(entry_p - base_sl)
                realized_r = abs(take_profit - entry_p) / (risk_dist + 1e-8)
                cursor.execute(
                    "UPDATE live_book SET exit_time=?, realized_r=?, status='CLOSED' WHERE id=?",
                    (current_time_str, realized_r, trade_id)
                )
                print(f"  🏆 [EXIT ALERT] {asset} {style} smashed Take-Profit at {take_profit}. Realized: +{realized_r:.2f}R")
                
            # 3. Dynamic MTF Trailing Management Step
            elif ltf_close <= mtf_trail and style in ["SET_3_SHORT_POSITION", "SET_4_INTRADAY_EXPANSION"]:
                risk_dist = abs(entry_p - base_sl)
                trail_r = (mtf_trail - entry_p) / (risk_dist + 1e-8)
                cursor.execute(
                    "UPDATE live_book SET exit_time=?, realized_r=?, status='CLOSED' WHERE id=?",
                    (current_time_str, max(-1.0, trail_r), trade_id)
                )
                print(f"  🔄 [TRAIL ALERT] {asset} {style} closed below MTF protection line. Realized: {trail_r:+.2f}R")
            else:
                # Update trailing stop markers step-by-step as the structural baseline scales up
                if mtf_trail > current_sl:
                    cursor.execute("UPDATE live_book SET current_sl=? WHERE id=?", (mtf_trail, trade_id))
                    
            conn.commit()
            conn.close()
            return

        # --- EVALUATE SIGNALS ONLY ON THE CLOSED STREAM BOUNDARY ---
        if htf_row['bull_bias'] and mtf_row['bull_trend'] and ltf_row['bull_trigger'] and mtf_row['bull_pullback']:
            entry_price = ltf_row['close']
            sl = ltf_row['strong_support_zone']
            tp = htf_row['weak_high_target']
            
            risk_dist = entry_price - sl
            if risk_dist <= 0: 
                conn.close()
                return
                
            computed_rr = (tp - entry_price) / risk_dist
            
            # Strict verification parameter gate
            if computed_rr >= 4.0:
                cursor.execute("""
                    INSERT INTO live_book (asset, style, direction, entry_time, entry_price, sl, tp, current_sl, exit_time, realized_r, status)
                    VALUES (?, ?, 'LONG', ?, ?, ?, ?, ?, 'OPEN', 0.0, 'ACTIVE')
                """, (asset, style, current_time_str, entry_price, sl, tp, sl))
                print(f"  🚀 [ENTRY TRIGGERED] {asset} {style} Entered Long at {entry_price} | Target: {tp} ({computed_rr:.1f}R potential)")

        conn.commit()
        conn.close()

    def simulate_streaming_feed(self):
        """Simulates incoming WebSocket ticks to verify state performance metrics."""
        print("==========================================================================================")
        print(" 🛰️ APEX QUANT OS V3.0: STREAMING POSITION MANAGER VALIDATION")
        print("==========================================================================================")
        print("[*] Initializing empty streaming buffer slots...")
        
        # Mocking an isolated data packet stream event
        mock_htf = {'bull_bias': True, 'weak_high_target': 105000.0}
        mock_mtf = {'bull_trend': True, 'bull_pullback': True, 'ema_fast': 99500.0}
        mock_ltf = {'bull_trigger': True, 'close': 100000.0, 'low': 99800.0, 'high': 100200.0, 'strong_support_zone': 99000.0}
        
        print("[*] Ingesting streaming packet tick across tracking filters...")
        self.process_live_candle_tick("BTCUSDT", "SET_4_INTRADAY_EXPANSION", mock_htf, mock_mtf, mock_ltf)
        
        # Re-query database to verify data persistence
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM live_book", conn)
        conn.close()
        
        print("\n[VIRTUAL STORAGE PERSISTENCE AUDIT LOGS]")
        print("------------------------------------------------------------------------------------------")
        print(df.to_string(index=False))
        print("==========================================================================================")

if __name__ == "__main__":
    processor = LiveStateProcessor()
    processor.simulate_streaming_feed()
