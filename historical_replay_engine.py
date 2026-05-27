import json
import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

from core.regime_classifier import RegimeEngine
from structure_engine.swing_detector import StructureEngine
from structure_engine.displacement_detector import DisplacementEngine
from core.scoring_engine import ConcurrencyScoringEngine
from master_orchestrator import MasterOrchestrator
from dataset_bootstrapper import LocalDataFeedEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

DB_PATH = Path("./storage/apex_systems.db")

class DynamicReplayChamber:
    def __init__(self, profile):
        self.profile = profile
        self.orchestrator = MasterOrchestrator()
        
        self.regime_engine = RegimeEngine()
        self.structure_engine = StructureEngine(lookback=5)
        self.displacement_engine = DisplacementEngine(lookback=5, threshold_multiplier=profile.displacement_threshold)
        self.scoring_engine = ConcurrencyScoringEngine(target_threshold=profile.target_threshold)
        
        self.active_trades = {} 
        
        # In-Memory Telemetry Buffers
        self._trade_buffer = []
        self._denial_buffer = []
        
        self._init_database_tables()
        print(f"[*] Dynamic Replay Chamber primed with profile cartridge: [{profile.name}]")

    def _init_database_tables(self):
        """Initializes structural database schemas inside a single connectivity layer."""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS closed_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                profile TEXT,
                regime TEXT,
                entry_price REAL,
                exit_price REAL,
                pnl_percent REAL,
                outcome TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS denied_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                regime TEXT,
                displacement REAL,
                score REAL,
                reason TEXT,
                price REAL
            )
        """)
        conn.commit()
        conn.close()

    def run_time_warp(self, symbol, lookback_minutes=300):
        """Executes zero-latency in-memory timeline simulations using high-speed records mapping."""
        engine = LocalDataFeedEngine()
        csv_config = {"timestamp": 0, "open": 1, "high": 2, "low": 3, "close": 4, "volume": 5}
        
        try:
            feed = engine.stream_chronological_feed(symbol, schema=csv_config)
            records = list(feed)
            if not records:
                print(f"[🔴 ERROR] Ingestion matrix empty for target: {symbol}")
                return
                
            if lookback_minutes:
                records = records[-lookback_minutes:]
                
            parsed_records = []
            for r in records:
                ts = float(r["timestamp"])
                while ts > 2.5 * 10**9:
                    ts /= 10.0
                parsed_records.append({
                    "start_time": datetime.fromtimestamp(ts),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"])
                })
                
            df_raw = pd.DataFrame(parsed_records)
            total_ticks = len(df_raw)
            warmup_bars = 30
            
            if total_ticks <= warmup_bars:
                return

            print(f"[⚡ VECTORIZER] Precomputing full indicator matrix across {total_ticks} candles for {symbol}...")
            df_global = self.structure_engine.detect_swings(df_raw)

            # High-Speed Optimization: Convert DataFrame completely to a native Python list of dicts
            global_records = df_global.to_dict('records')

            print(f"[🚀 ENGINE] Running unchained dictionary-mapped loop over {total_ticks} ticks...")

            # --- Structural Try-Finally Block: Secures memory logs against manual cancellations ---
            try:
                for i in range(warmup_bars, total_ticks):
                    current_row = global_records[i]
                    
                    # --- Stateful Open Position Lifecycle Manager ---
                    if symbol in self.active_trades:
                        trade = self.active_trades[symbol]
                        hit_stop = current_row['low'] <= trade['sl']
                        hit_target = current_row['high'] >= trade['tp']
                        
                        if hit_stop or hit_target:
                            exit_price = trade['sl'] if hit_stop else trade['tp']
                            pnl = ((exit_price - trade['entry_price']) / trade['entry_price']) * 100
                            outcome = "STOP_LOSS" if hit_stop else "TAKE_PROFIT"
                            
                            self._trade_buffer.append((
                                str(current_row['start_time']), symbol, self.profile.name,
                                trade['regime'], trade['entry_price'], exit_price, pnl, outcome
                            ))
                            
                            print(f"   🛑 [{self.profile.name}] EXIT {symbol} realized at ${exit_price:.2f} | PnL: {pnl:+.2f}% [{outcome}]")
                            del self.active_trades[symbol]
                            continue 
                    
                    # Construct lightweight micro-windows only when requested by target modules
                    window_slice = global_records[max(0, i - 30):i + 1]
                    df_slice = pd.DataFrame(window_slice)
                    
                    # --- Dynamic Regime Extraction ---
                    current_regime = "NORMAL"
                    method_candidates = ['classify_regime', 'predict_regime', 'get_regime', 'detect_regime', 'classify']
                    chosen_method = next((m for m in method_candidates if hasattr(self.regime_engine, m)), None)
                    if chosen_method:
                        try:
                            current_regime = getattr(self.regime_engine, chosen_method)(df_slice)
                        except Exception: pass

                    if isinstance(current_regime, (pd.DataFrame, pd.Series)):
                        if not current_regime.empty:
                            scalar_val = current_regime.iloc[-1, -1] if isinstance(current_regime, pd.DataFrame) else current_regime.iloc[-1]
                            current_regime = str(scalar_val.iloc[0]) if isinstance(scalar_val, pd.Series) else str(scalar_val)
                        else: current_regime = "NORMAL"
                    current_regime = str(current_regime).upper().strip()

                    # --- Core Strategy Evaluation Gates ---
                    sweep_detected = bool(current_row.get('Sweep_Event', False)) or bool(current_row.get('Recent_Bullish_Sweep', False))
                    execution_unlocked = bool(current_row.get('Execution_Unlocked', True))
                    struct_signals = {"high_signal": sweep_detected, "low_signal": sweep_detected}
                    
                    try: disp_metrics = self.displacement_engine.validate_displacement(df_slice)
                    except Exception: disp_metrics = {'ratio': 1.0}
                        
                    score_payload = self.scoring_engine.calculate_execution_score(current_regime, struct_signals, disp_metrics)
                    
                    if not score_payload["execution_authorized"] or not execution_unlocked:
                        if sweep_detected:
                            self._denial_buffer.append((
                                str(current_row['start_time']), symbol, current_regime,
                                float(disp_metrics.get('ratio', 1.0)), float(score_payload.get("conviction_score", 0.0)),
                                f"Profile [{self.profile.name}] Sweep-Gate Blocked", float(current_row['close'])
                            ))
                        continue
                        
                    # --- Stateful Entry Gate: Enforcing Strict Structural Asymmetry ---
                    if symbol not in self.active_trades:
                        clearance = self.orchestrator.request_execution_clearance(symbol, "LONG", self.profile.risk_per_trade)
                        if clearance["status"] == "DENIED":
                            self._denial_buffer.append((
                                str(current_row['start_time']), symbol, current_regime,
                                float(disp_metrics.get('ratio', 1.0)), float(score_payload.get("conviction_score", 0.0)),
                                f"Orchestrator Block -> {clearance['reason']}", float(current_row['close'])
                            ))
                        else:
                            entry_p = float(current_row['close'])
                            raw_local_low = current_row.get('local_low', entry_p * 0.99)
                            
                            if pd.isna(raw_local_low) or raw_local_low >= entry_p or raw_local_low < entry_p * 0.85:
                                sl_p = entry_p * 0.99
                            else:
                                sl_p = float(raw_local_low) * 0.999 
                                
                            risk_distance = entry_p - sl_p
                            reward_multiplier = 10.0
                            tp_p = entry_p + (risk_distance * reward_multiplier)
                            
                            realized_rr = (tp_p - entry_p) / (entry_p - sl_p) if (entry_p - sl_p) > 0 else 0
                            if realized_rr < 4.0:
                                tp_p = entry_p + (risk_distance * 4.0)
                            
                            self.active_trades[symbol] = {
                                "entry_price": entry_p,
                                "sl": sl_p,
                                "tp": tp_p,
                                "regime": current_regime
                            }
                            print(f"🔥 [{self.profile.name}] ENTRY {symbol} executed at ${entry_p:.2f} | SL: ${sl_p:.2f} | TP: ${tp_p:.2f} [Structural RR -> 1:{reward_multiplier:.0f}]")
                
                print(f"[✓] Processing loop completed for {symbol}.")

            finally:
                # This block runs automatically even if the script is terminated via Ctrl+C
                self._flush_buffers_to_storage()
            
        except Exception as e:
            print(f"[-] Time warp simulation aborted: {e}")

    def _flush_buffers_to_storage(self):
        """Flushes buffered records to the database disk layer using atomic batch queries."""
        if not self._trade_buffer and not self._denial_buffer:
            return
            
        print(f"[💾 ATOMIC FLUSH] Writing buffered telemetry records to disk storage...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            if self._trade_buffer:
                cursor.executemany("""
                    INSERT INTO closed_trades (timestamp, symbol, profile, regime, entry_price, exit_price, pnl_percent, outcome)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, self._trade_buffer)
                print(f"  └── [✓] Saved {len(self._trade_buffer)} completed trade records to ledger.")
                self._trade_buffer.clear()
                
            if self._denial_buffer:
                cursor.executemany("""
                    INSERT INTO denied_signals (timestamp, symbol, regime, displacement, score, reason, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, self._denial_buffer)
                print(f"  └── [✓] Saved {len(self._denial_buffer)} filtration logs to ledger.")
                self._denial_buffer.clear()
                
            conn.commit()
        except Exception as e:
            print(f"  └── [🔴 DATABASE ERROR] Atomic flush failed: {e}")
        finally:
            conn.close()
