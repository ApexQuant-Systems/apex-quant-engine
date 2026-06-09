import os
import sys
import time
import sqlite3
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

class AutonomousExecutionEngine:
    """
    Apex Quant OS v3.0: Institutional Risk & Resilient Execution Engine.
    Handles fault-tolerant data pipelines, structural portfolio heat caps,
    adaptive risk-sizing rules, and smart software anomaly circuit breakers.
    """
    def __init__(self):
        self.db_path = "./data/forward_testing_vault.db"
        self.assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self.base_url = "https://api.binance.com/api/v3/klines"
        self.system_frozen = False
        self.init_db_structures()

    def init_db_structures(self):
        """Guarantees underlying structural databases are indexed cleanly."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS live_book (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT,
                style TEXT,
                direction TEXT,
                entry_time TEXT,
                entry_price REAL,
                sl REAL,
                tp REAL,
                current_sl REAL,
                exit_time TEXT,
                realized_r REAL,
                status TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                asset TEXT,
                rule_violated TEXT,
                current_price REAL
            )
        ''')
        conn.commit()
        conn.close()

    def log_risk_rejection(self, asset, reason, current_price):
        """Logs blocked strategy signals into the database for dashboard visibility."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            timestamp_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO risk_alerts (timestamp, asset, rule_violated, current_price)
                VALUES (?, ?, ?, ?)
            ''', (timestamp_str, asset, reason, current_price))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  ⚠️ Failed to write risk exception log: {e}")

    def fetch_candles_with_retry(self, symbol, interval="15m", limit=100, retries=3, backoff_seconds=2):
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        for attempt in range(1, retries + 1):
            try:
                response = requests.get(self.base_url, params=params, timeout=5)
                if response.status_code == 200:
                    raw = response.json()
                    df = pd.DataFrame(raw, columns=[
                        'open_time', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_asset_volume', 'number_of_trades',
                        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                    ])
                    df['datetime'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    return df.set_index('datetime')
            except Exception:
                pass
            if attempt < retries:
                time.sleep(backoff_seconds * attempt)
        return pd.DataFrame()

    def detect_software_anomalies(self, candidate_asset):
        """Smarter Software Anomaly Engine to shield against database write floods."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM live_book WHERE asset = ? AND status = 'ACTIVE'", (candidate_asset,))
            if cursor.fetchone()[0] > 0:
                print(f"  🚨 [WATCHDOG SHUTDOWN] Loop Anomaly: Duplicate active slots attempted for {candidate_asset}.")
                self.system_frozen = True
                conn.close()
                return True
            one_min_ago = (datetime.now(timezone.utc) - timedelta(seconds=60)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("SELECT COUNT(*) FROM live_book WHERE asset = ? AND entry_time >= ?", (candidate_asset, one_min_ago))
            if cursor.fetchone()[0] > 0:
                print(f"  🚨 [WATCHDOG SHUTDOWN] Database Flood: Multiple entries written for {candidate_asset} within 60s.")
                self.system_frozen = True
                conn.close()
                return True
            conn.close()
            return False
        except Exception as e:
            print(f"  ⚠️ Watchdog process failure: {e}")
            return True

    def calculate_adaptive_allocation_risk(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT realized_r FROM live_book WHERE status = 'CLOSED' ORDER BY id DESC LIMIT 5")
            historical_sample = cursor.fetchall()
            conn.close()
            if len(historical_sample) < 5: return 1.0
            if all(row[0] < 0 for row in historical_sample):
                return 0.5
            return 1.0
        except Exception:
            return 1.0

    def check_portfolio_bounds(self, asset):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT asset FROM live_book WHERE status = 'ACTIVE'")
        active_rows = cursor.fetchall()
        conn.close()
        
        active_assets = [row[0] for row in active_rows]
        
        if asset in active_assets:
            return False, "Duplicate Asset Shield Active"
        if len(active_assets) >= 6:
            return False, "Max Portfolio Heat Ceiling Reached (6 Slots)"
        
        crypto_tickers = [a for a in active_assets if "USDT" in a]
        if len(crypto_tickers) >= 3 and "USDT" in asset:
            return False, "Max Correlated Crypto Exposure Exceeded (3 Assets)"
            
        return True, "Passed Risk Assays"

    def execute_paper_entry(self, asset, strategy, price, sl, tp):
        if self.detect_software_anomalies(asset): return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO live_book (asset, style, direction, entry_time, entry_price, sl, tp, current_sl, exit_time, realized_r, status)
            VALUES (?, ?, 'LONG', ?, ?, ?, ?, ?, NULL, 0.0, 'ACTIVE')
        ''', (asset, strategy, timestamp, price, sl, tp, sl))
        conn.commit()
        conn.close()
        print(f"🚀 [AUTOMATED RISK ENTRY] Long {asset} at {price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}")

    def execute_paper_exit(self, trade_id, asset, exit_price, realized_r, reason):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            UPDATE live_book SET status = 'CLOSED', exit_time = ?, realized_r = ?, current_sl = ? WHERE id = ?
        ''', (timestamp, realized_r, exit_price, trade_id))
        
        cursor.execute("SELECT balance FROM paper_wallet WHERE account_id = 'APEX_PAPER_01'")
        wallet_balance = cursor.fetchone()[0]
        risk_percentage = self.calculate_adaptive_allocation_risk()
        risk_dollars = wallet_balance * (risk_percentage * 0.01)
        pnl_dollars = realized_r * risk_dollars
        new_balance = wallet_balance + pnl_dollars
        
        cursor.execute("UPDATE paper_wallet SET balance = ?, updated_at = ? WHERE account_id = 'APEX_PAPER_01'", (new_balance, timestamp))
        conn.commit()
        conn.close()
        print(f"💥 [CLOSED STATE LOGGED] Asset {asset} Exit via {reason} | Outcome: {realized_r:+.2f}R (${pnl_dollars:+.2f})")

    def process_asset_lifecycle(self, asset):
        df_15m = self.fetch_candles_with_retry(asset, interval="15m", limit=100)
        if df_15m.empty: 
            return "⚠️ NETWORK OUTAGE FALLBACK"

        ohlc_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_1h = df_15m.resample('1h').agg(ohlc_rules).dropna()
        df_4h = df_15m.resample('4h').agg(ohlc_rules).dropna()
        if len(df_4h) < 5 or len(df_1h) < 5 or len(df_15m) < 5: return "❌ INSUFFICIENT DATA LOAD"

        ema_4h = df_4h['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        htf_bias = df_4h['close'].iloc[-1] > ema_4h
        ema_fast_1h = df_1h['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema_slow_1h = df_1h['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        mtf_trend = ema_fast_1h > ema_slow_1h

        current_price = float(df_15m['close'].iloc[-1])
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, entry_price, current_sl, tp FROM live_book WHERE asset = ? AND status = 'ACTIVE'", (asset,))
        active_trade = cursor.fetchone()
        conn.close()

        # Format explicit component tokens for visualization clarity
        htf_token = "✅ HTF" if htf_bias else "❌ HTF"
        mtf_token = "✅ MTF" if mtf_trend else "❌ MTF"

        if active_trade:
            trade_id, entry_p, current_sl, target_tp = active_trade
            if current_price <= current_sl:
                self.execute_paper_exit(trade_id, asset, current_sl, -1.0, "STOP LOSS BREACH")
            elif current_price >= target_tp:
                risk_distance = entry_p - current_sl if entry_p > current_sl else (entry_p * 0.02)
                realized_r = (target_tp - entry_p) / risk_distance
                self.execute_paper_exit(trade_id, asset, target_tp, realized_r, "TAKE PROFIT LIMIT")
            else:
                if mtf_trend and ema_fast_1h > current_sl and current_price > entry_p:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE live_book SET current_sl = ? WHERE id = ?", (float(ema_fast_1h), trade_id))
                    conn.commit()
                    conn.close()
            return f"🛡️ ACTIVE MANAGING | Price: {current_price:,.2f}"
        else:
            if htf_bias and mtf_trend:
                passed_risk, restriction_reason = self.check_portfolio_bounds(asset)
                if passed_risk:
                    local_low_5x = df_15m['low'].rolling(5).min().iloc[-1]
                    target_high_5x = df_4h['high'].rolling(5).max().iloc[-1]
                    stop_distance = current_price - local_low_5x
                    reward_distance = target_high_5x - current_price
                    if stop_distance > 0:
                        rr_ratio = reward_distance / stop_distance
                        if rr_ratio >= 4.0:
                            self.execute_paper_entry(asset, "SET_4_INTRADAY_EXPANSION", current_price, local_low_5x, target_high_5x)
                            return f"🚀 ENTRY APPROVED | {htf_token} | {mtf_token} | ✅ RR ({rr_ratio:.1f}R)"
                        else:
                            self.log_risk_rejection(asset, f"Rejected RR Ratio ({rr_ratio:.2f}R < 4.0R)", current_price)
                            return f"🛑 REJECTED RISK PROFILE | {htf_token} | {mtf_token} | ❌ RR ({rr_ratio:.1f}R)"
                else:
                    self.log_risk_rejection(asset, restriction_reason, current_price)
                    return f"🛑 RISK SHIELD INTERVENTION | {restriction_reason.upper()}"
            
            return f"🔍 SCANNING TELEMETRY | {htf_token} | {mtf_token} | Decision: NO TRADE -> Price: {current_price:,.2f}"

    def print_high_fidelity_diagnostics(self, individual_states):
        """Formats the explicit scannable reporting layout requested by the auditor."""
        print(f"\n⚡ [CLOCK TICK: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC]")
        for asset, state_str in individual_states.items():
            print(f"  ├── {asset:9s} : {state_str}")
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT asset FROM live_book WHERE status = 'ACTIVE'")
            active_trades = len(cursor.fetchall())
            conn.close()
        except Exception:
            active_trades = 0
            
        current_heat = active_trades * 1.0
        print(f"  📊 Portfolio Heat: {current_heat:.1f}% | Active Slots: {active_trades}/6 | Status: NORMAL")

    def run_engine_loop(self):
        print("==========================================================================================")
        print(" 🛰️ APEX QUANT OS V3.0 : AUTONOMOUS RISK OPERATING SYSTEM ENGINE")
        print("==========================================================================================")
        print(" [*] Core Safeguards: Max 6% Heat | Max 3% Crypto | Adaptive Sizing | Smart Watchdog Activated")
        
        while True:
            if self.system_frozen:
                print("\n 🚨 [CRITICAL HALT] System has frozen due to a targeted Watchdog trigger. Manual audit required.")
                time.sleep(10)
                continue
                
            states_ledger = {}
            for asset in self.assets:
                states_ledger[asset] = self.process_asset_lifecycle(asset)
                
            self.print_high_fidelity_diagnostics(states_ledger)
            time.sleep(60)

if __name__ == "__main__":
    engine = AutonomousExecutionEngine()
    engine.run_engine_loop()
