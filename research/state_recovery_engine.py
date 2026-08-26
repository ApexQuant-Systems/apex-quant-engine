import sqlite3
import os
from dataclasses import dataclass, asdict

@dataclass
class OperationalState:
    is_recovered: bool
    active_exposure_pct: float
    tracked_positions: dict
    pending_order_count: int

class StateRecoveryEngine:
    """
    🛰️ APEX INFRASTRUCTURE SYSTEM: DETERMINISTIC STATE RECOVERY PRIMITIVE
    Reconstructs execution memory structures from persistent disk ledgers post-crash.
    """
    def __init__(self, db_path: str = "data/forward_testing_vault.db"):
        self.db_path = db_path

    def reconstruct_runtime_memory(self) -> OperationalState:
        print("🔍 Scanning database vault partitions to extract unclosed session states...")
        
        if not os.path.exists(self.db_path):
            print("  ⚠️ No legacy system ledger discovered on disk. Instantiating fresh memory cache.")
            return OperationalState(is_recovered=False, active_exposure_pct=0.0, tracked_positions={}, pending_order_count=0)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Recover active open trade positions to anchor risk controls
        cursor.execute("SELECT symbol, entry_price, sl_price, tp_price, current_exposure FROM positions WHERE status='ACTIVE'")
        open_rows = cursor.fetchall()
        
        recovered_positions = {}
        total_exposure = 0.0
        
        for row in open_rows:
            symbol, entry_price, sl_price, tp_price, exposure = row
            recovered_positions[symbol] = {
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "exposure_allocated": exposure
            }
            total_exposure += exposure
            print(f"  ├── [RECOVERED POSITION] Active trade found for {symbol} | Risk: {exposure*100:.1f}%")

        # 2. Trace pending orders frozen in the execution queue
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status='SUBMITTED' OR status='PENDING'")
        pending_order_count = cursor.fetchone()[0]
        
        conn.close()
        
        return OperationalState(
            is_recovered=True if len(recovered_positions) > 0 else False,
            active_exposure_pct=total_exposure,
            tracked_positions=recovered_positions,
            pending_order_count=pending_order_count
        )

if __name__ == "__main__":
    print("=====================================================================")
    print(" 🛰️ APEX INFRASTRUCTURE: TEST TRIGGERING STATE RECOVERY LOOP")
    print("=====================================================================")
    
    # Pre-populate dummy active state boundaries inside our vault to verify parser reliability
    db_file = "data/forward_testing_vault.db"
    connection = sqlite3.connect(db_file)
    cur = connection.cursor()
    
    # Clear old values to run a clean simulation test
    cur.execute("DELETE FROM positions;")
    cur.execute("DELETE FROM orders;")
    
    # Inject a simulated live position that was running when the system supposedly crashed
    cur.execute("INSERT INTO positions VALUES ('BTCUSDT', 1718222000000, 68500.0, 67200.0, 73700.0, 0.01, 'ACTIVE');")
    cur.execute("INSERT INTO orders VALUES ('ORD_9999_X', 1718222000000, 'BTCUSDT', 'SET_4_INTRADAY', 'LONG', 68500.0, 'PENDING');")
    connection.commit()
    connection.close()
    
    # Instantiate the recovery framework
    recovery_layer = StateRecoveryEngine()
    system_state = recovery_layer.reconstruct_runtime_memory()
    
    print("-" * 69)
    print(f"🏁 STATE RECOVERY METRICS LOGGED:")
    print(f"  ├── Status            : {'🟢 SUCCESSFUL RECONSTRUCTION' if system_state.is_recovered else '🟢 FRESH CACHE INITIALIZED'}")
    print(f"  ├── Recovered Exposure: {system_state.active_exposure_pct*100:.1f}% Exposure Account Space")
    print(f"  └── Queue Orphaning   : {system_state.pending_order_count} Pending Orders Tracked")
    print("=====================================================================")
