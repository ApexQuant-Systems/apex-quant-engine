import json
import os
import sys
import sqlite3
import pandas as pd
import numpy as np
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
        self._trade_buffer = []
        self._denial_buffer = []
        
        # Performance Cache Layer: Discover reflection method hooks once on initialization
        method_candidates = ['classify_regime', 'predict_regime', 'get_regime', 'detect_regime', 'classify']
        self._chosen_regime_method = next((m for m in method_candidates if hasattr(self.regime_engine, m)), None)
        
        self._init_database_tables()
        print(f"[*] Macro Replay Chamber activated for structural hierarchy: [{profile.name}]")

    def _init_database_tables(self):
        """Initializes relational telemetry tracking ledgers."""
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

    def run_time_warp(self, symbol, lookback_minutes=None):
        """
        Executes a high-velocity simulation projecting macro structural environments 
        directly onto your baseline tracking layer without fragile table merges.
        """
        engine = LocalDataFeedEngine()
        csv_config = {"timestamp": 0, "open": 1, "high": 2, "low": 3, "close": 4, "volume": 5}
        
        try:
            # Ingests baseline raw candle streams
            feed = engine.stream_chronological_feed(symbol, schema=csv_config)
            records = list(feed)
            if not records: 
                print(f"[🔴 ERROR] Data feed ingestion failed for target asset: {symbol}")
                return
                
            parsed_records = []
            for r in records:
                ts = float(r["timestamp"])
                while ts > 2.5 * 10**9: ts /= 10.0
                parsed_records.append({
                    "start_time": datetime.fromtimestamp(ts),
                    "open": float(r["open"]), "high": float(r["high"]),
                    "low": float(r["low"]), "close": float(r["close"])
                })
                
            df_working = pd.DataFrame(parsed_records)
            total_ticks = len(df_working)
            if total_ticks <= 200: 
                print(f"[⚠️ WARNING] Insufficient baseline rows for {symbol}. Ingestion matrix too small.")
                return 

            print(f"\n[⚡ VECTOR SYNCHRONIZER] Projecting 4H Macro Boundaries onto timeline for {symbol}...")
            df_working.sort_values('start_time', inplace=True)
            
            # --- PHASE 1: Direct Vector Macro Projector ---
            # 20 periods of 4-hour blocks = 320 baseline units on a 15m stream.
            # Shifting by 1 strictly enforces closed-bar context, eliminating look-ahead bias.
            rolling_4h_high = df_working['high'].rolling(320, min_periods=1).max()
            rolling_4h_low = df_working['low'].rolling(320, min_periods=1).min()
            
            df_working['four_hour_equilibrium'] = ((rolling_4h_high + rolling_4h_low) / 2.0).shift(1)
            df_working['four_hour_equilibrium'] = df_working['four_hour_equilibrium'].bfill()

            print(f"[🧠 PRECOMPUTING] Mapping indicators and local swings across {total_ticks} execution rows...")
            df_global = self.structure_engine.detect_swings(df_working.reset_index(drop=True))
            
            regimes = ["NORMAL"] * total_ticks
            displacement_ratios = [1.0] * total_ticks
            
            # Complete technical pre-calculation pass
            for i in range(30, total_ticks):
                df_slice = df_global.iloc[max(0, i - 30):i + 1]
                
                current_regime = "NORMAL"
                if self._chosen_regime_method:
                    try: current_regime = getattr(self.regime_engine, self._chosen_regime_method)(df_slice)
                    except Exception: pass
                if isinstance(current_regime, (pd.DataFrame, pd.Series)) and not current_regime.empty:
                    scalar_val = current_regime.iloc[-1, -1] if isinstance(current_regime, pd.DataFrame) else current_regime.iloc[-1]
                    current_regime = str(scalar_val)
                regimes[i] = str(current_regime).upper().strip()
                
                try:
                    disp_metrics = self.displacement_engine.validate_displacement(df_slice)
                    displacement_ratios[i] = float(disp_metrics.get('ratio', 1.0))
                except Exception: pass

            df_global['calculated_regime'] = regimes
            df_global['displacement_ratio'] = displacement_ratios
            
            # Convert matrix to native primitive records to bypass index iteration drag
            global_records = df_global.to_dict('records')
            print(f"[🚀 ENGINE] Launching hierarchical context state machine over {total_ticks} ticks...")

            # --- PHASE 2: Lightweight Replay Loop ---
            for i in range(30, total_ticks):
                current_row = global_records[i]
                
                # --- Stateful Open Position Lifecycle Manager ---
                if symbol in self.active_trades:
                    trade = self.active_trades[symbol]
                    
                    if not trade['tranche_a_hit']:
                        if current_row['low'] <= trade['sl']:
                            pnl = ((trade['sl'] - trade['entry_price']) / trade['entry_price']) * 100
                            self._trade_buffer.append((str(current_row['start_time']), symbol, self.profile.name, trade['regime'], trade['entry_price'], trade['sl'], pnl, "STOP_LOSS_FULL"))
                            print(f"   🛑 [{self.profile.name}] MACRO INVALIDATION hit for {symbol} | PnL: {pnl:+.2f}%")
                            del self.active_trades[symbol]
                            continue
                        elif current_row['high'] >= trade['tp_a']:
                            trade['tranche_a_hit'] = True
                            trade['sl'] = trade['entry_price'] # Lock trailing stop to break-even floor
                            print(f"   💵 [{self.profile.name}] TRANCHE A Anchor Hit for {symbol} at ${trade['tp_a']:.2f} [1:4 Secured]")
                    else:
                        if current_row['low'] <= trade['sl']:
                            pnl = ((trade['tp_a'] + trade['entry_price']) / 2.0 - trade['entry_price']) / trade['entry_price'] * 100
                            self._trade_buffer.append((str(current_row['start_time']), symbol, self.profile.name, trade['regime'], trade['entry_price'], trade['entry_price'], pnl, "PARTIAL_BREAK_EVEN"))
                            print(f"   🛑 [{self.profile.name}] RUNNER stopped at BE floor for {symbol} | Combined PnL: {pnl:+.2f}%")
                            del self.active_trades[symbol]
                            continue
                        elif current_row['high'] >= trade['tp_b']:
                            pnl = ((trade['tp_a'] + trade['tp_b']) / 2.0 - trade['entry_price']) / trade['entry_price'] * 100
                            self._trade_buffer.append((str(current_row['start_time']), symbol, self.profile.name, trade['regime'], trade['entry_price'], trade['tp_b'], pnl, "TAKE_PROFIT_MAX"))
                            print(f"   🚀 [{self.profile.name}] MACRO RUNNER TARGET EXPANSION for {symbol} at ${trade['tp_b']:.2f} | Net Combined PnL: {pnl:+.2f}% [1:6 Clear]")
                            del self.active_trades[symbol]
                            continue

                # --- Strategy Entry Evaluation Gates ---
                current_regime = current_row['calculated_regime']
                sweep_detected = bool(current_row.get('Sweep_Event', False)) or bool(current_row.get('Recent_Bullish_Sweep', False))
                execution_unlocked = bool(current_row.get('Execution_Unlocked', True))
                
                # --- OPTIMIZED VALUE FILTER ---
                entry_price_basis = float(current_row['close'])
                four_hour_eq = float(current_row['four_hour_equilibrium'])
                
                # System permits sniper execution ONLY when price trades inside the 4H Discount Zone
                macro_hierarchy_aligned = entry_price_basis < four_hour_eq
                
                struct_signals = {"high_signal": sweep_detected, "low_signal": sweep_detected}
                disp_metrics = {'ratio': current_row['displacement_ratio']}
                score_payload = self.scoring_engine.calculate_execution_score(current_regime, struct_signals, disp_metrics)
                
                if not score_payload["execution_authorized"] or not execution_unlocked or not macro_hierarchy_aligned:
                    if sweep_detected:
                        reason = "HTF 4H Premium Lockout" if not macro_hierarchy_aligned else f"Profile [{self.profile.name}] Sweep-Gate Blocked"
                        self._denial_buffer.append((str(current_row['start_time']), symbol, current_regime, float(disp_metrics['ratio']), float(score_payload.get("conviction_score", 0.0)), reason, entry_price_basis))
                    continue
                    
                # --- Allocation Layer: Entry Routing ---
                if symbol not in self.active_trades:
                    clearance = self.orchestrator.request_execution_clearance(symbol, "LONG", self.profile.risk_per_trade)
                    if clearance["status"] == "DENIED":
                        self._denial_buffer.append((str(current_row['start_time']), symbol, current_regime, float(disp_metrics['ratio']), float(score_payload.get("conviction_score", 0.0)), f"Orchestrator Block -> {clearance['reason']}", entry_price_basis))
                    else:
                        raw_local_low = current_row.get('local_low', entry_price_basis * 0.99)
                        if pd.isna(raw_local_low) or raw_local_low >= entry_price_basis or raw_local_low < entry_price_basis * 0.85:
                            sl_p = entry_price_basis * 0.99
                        else:
                            sl_p = float(raw_local_low) * 0.999 
                            
                        risk_distance = entry_price_basis - sl_p
                        
                        # Multi-Style Brackets: 1:4 structural swing target / 1:6 macro target
                        tp_a_target = entry_price_basis + (risk_distance * 4.0)  
                        tp_b_target = entry_price_basis + (risk_distance * 6.0) 
                        
                        self.active_trades[symbol] = {
                            "entry_price": entry_price_basis, "sl": sl_p,
                            "tp_a": tp_a_target, "tp_b": tp_b_target,
                            "regime": current_regime, "tranche_a_hit": False
                        }
                        print(f"🔥 [{self.profile.name}] 4H-DISCOUNT ENTRY for {symbol} at ${entry_price_basis:.2f} | Stop: ${sl_p:.2f} | Tgt A: ${tp_a_target:.2f} | Tgt B: ${tp_b_target:.2f}")
            
            print(f"[✓] Hierarchical structural loop completed for {symbol}.")
        except Exception as e:
            print(f"[-] Time warp simulation aborted: {e}")
        finally:
            self._flush_buffers_to_storage()

    def _flush_buffers_to_storage(self):
        if not self._trade_buffer and not self._denial_buffer: return
        print(f"[💾 ATOMIC FLUSH] Writing buffered structural macro records to disk storage...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            if self._trade_buffer:
                cursor.executemany("INSERT INTO closed_trades (timestamp, symbol, profile, regime, entry_price, exit_price, pnl_percent, outcome) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", self._trade_buffer)
                self._trade_buffer.clear()
            if self._denial_buffer:
                cursor.executemany("INSERT INTO denied_signals (timestamp, symbol, regime, displacement, score, reason, price) VALUES (?, ?, ?, ?, ?, ?, ?)", self._denial_buffer)
                self._denial_buffer.clear()
            conn.commit()
            print(f"  └── [✓] Ledger state permanently updated on disk database.")
        except Exception as e: print(f"  └── [🔴 DATABASE ERROR] Bulk write aborted: {e}")
        finally: conn.close()
