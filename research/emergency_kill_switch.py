import sqlite3
import os
import time

class EmergencyKillSwitch:
    """
    🛰️ APEX INFRASTRUCTURE SYSTEM: EMERGENCY HARD CIRCUIT BREAKER
    Monitors operational health vectors and acts as the final gate
    before allowing any order payload to hit live network routers.
    """
    def __init__(self, db_path: str = "data/forward_testing_vault.db", max_consecutive_errors: int = 5, max_drawdown_pct: float = 0.05):
        self.db_path = db_path
        self.max_errors = max_consecutive_errors
        self.max_dd = max_drawdown_pct

    def inspect_system_health(self) -> bool:
        """
        Evaluates real-time error frequency and account conditions.
        Returns True if the system is completely safe, False if a breach occurs.
        """
        if not os.path.exists(self.db_path):
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. Audit Error Frequency (Detect Loop Storms)
        # Scan recent system logs for repeated consecutive critical exceptions
        cursor.execute("SELECT COUNT(*) FROM system_events WHERE event_type='CRITICAL' AND timestamp > ?", (int(time.time() * 1000) - 60000,))
        recent_errors = cursor.fetchone()[0]

        if recent_errors >= self.max_errors:
            self._trigger_hard_freeze(cursor, f"Error storm detected. {recent_errors} critical errors logged within 60 seconds.")
            conn.commit()
            conn.close()
            return False

        # 2. Monitor Exposure & State Limits
        cursor.execute("SELECT COUNT(*) FROM positions WHERE status='ACTIVE'")
        active_slots = cursor.fetchone()[0]
        
        # Guardrail check against extreme phantom positions exceeding structural thresholds
        if active_slots > 6:
            self._trigger_hard_freeze(cursor, f"Structural exposure ceiling breach. Active slots: {active_slots}")
            conn.commit()
            conn.close()
            return False

        conn.close()
        return True

    def _trigger_hard_freeze(self, cursor, reason: str):
        """Executes a hard lockdown protocol inside the system state ledger."""
        print(f"\n🚨 [CIRCUIT BREAKER TRIGGERED] CRITICAL SYSTEM HALT DETECTED")
        print(f"  └── Reason: {reason}")
        
        # Log the intervention to the tracking log
        cursor.execute("""
            INSERT INTO system_events (timestamp, event_type, module_source, message)
            VALUES (?, 'SYSTEM_HALT', 'KILL_SWITCH', ?)
        """, (int(time.time() * 1000), f"HARD LOCKDOWN ACTIVATED: {reason}"))

if __name__ == "__main__":
    print("=====================================================================")
    print(" 🛰️ APEX INFRASTRUCTURE: EVALUATING EMERGENCY HALT PROTOCOLS")
    print("=====================================================================")
    
    kill_switch = EmergencyKillSwitch()
    
    # Pre-populate simulated logs to test nominal performance vs trigger breach
    db_file = "data/forward_testing_vault.db"
    connection = sqlite3.connect(db_file)
    cur = connection.cursor()
    
    # Scenario A: Nominal system state
    print("⚡ Scenario A: Evaluating health metrics under standard operation...")
    is_safe = kill_switch.inspect_system_health()
    print(f"  └── System Operational Status: {'🟢 SAFE TO EXECUTE' if is_safe else '🚨 LOCKED'}")
    
    # Scenario B: Simulating a critical error loop storm inside the ledger
    print("\n⚡ Scenario B: Injecting 5 rapid consecutive critical exceptions to simulate system failure...")
    for i in range(5):
        cur.execute("""
            INSERT INTO system_events (timestamp, event_type, module_source, message)
            VALUES (?, 'CRITICAL', 'WEBSOCKET_LAYER', 'Timeout handshake drop loop')
        """, (int(time.time() * 1000),))
    connection.commit()
    
    # Re-evaluate the switch condition
    is_safe_after_storm = kill_switch.inspect_system_health()
    print(f"  └── System Operational Status: {'🟢 SAFE TO EXECUTE' if is_safe_after_storm else '🚨 HARD FREEZE ACTIVE'}")
    
    # Clean up simulation tables
    cur.execute("DELETE FROM system_events WHERE event_type='CRITICAL' OR event_type='SYSTEM_HALT'")
    connection.commit()
    connection.close()
    print("=====================================================================")
