import os
import sys
import sqlite3
import time

class ApexForwardTestingVault:
    """
    🛰️ APEX WEALTH PLATFORM: PHASE 5 FORWARD TESTING VAULT
    Performs high-fidelity relational journaling of strategy signals,
    geometric parameters, and advanced trade observation metrics (MFE/MAE).
    """
    def __init__(self, db_path: str = "data/forward_testing_vault.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._initialize_vault_schema()

    def _initialize_vault_schema(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Deploying the comprehensive institutional statistical observation schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forward_signal_vault (
                signal_token TEXT PRIMARY KEY,
                timestamp INTEGER,
                set_id INTEGER,
                set_name TEXT,
                timeframe_map TEXT,
                symbol TEXT,
                asset_class TEXT,
                entry_price REAL,
                structural_sl REAL,
                structural_tp REAL,
                calculated_rr REAL,
                final_signal TEXT,
                max_favorable_excursion REAL, -- MFE: Peak profitability delta
                max_adverse_excursion REAL,    -- MAE: Maximum drawdown depth
                duration_seconds INTEGER,
                news_intensity_score TEXT      -- Economic event proximity marker
            )
        """)
        conn.commit()
        conn.close()
        print("  ├── [FORWARD VAULT] Relational Observation Vault Schemas Latched to Disk.")

    def log_forward_signal(self, p: dict):
        """Persists a complete analytical signal profile frame straight to disk storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO forward_signal_vault (
                    signal_token, timestamp, set_id, set_name, timeframe_map,
                    symbol, asset_class, entry_price, structural_sl, structural_tp,
                    calculated_rr, final_signal, max_favorable_excursion, max_adverse_excursion,
                    duration_seconds, news_intensity_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["signal_token"], p["timestamp"], p["set_id"], p["set_name"], p["timeframe_map"],
                p["symbol"], p["asset_class"], p["entry_price"], p["structural_sl"], p["structural_tp"],
                p["calculated_rr"], p["final_signal"], p.get("mfe", 0.0), p.get("mae", 0.0),
                p.get("duration", 0), p.get("news_score", "CLEAR")
            ))
            conn.commit()
        except Exception as e:
            print(f"  ❌ [VAULT STORAGE ERROR] Failed to record signal tracking row: {e}")
        finally:
            conn.close()
