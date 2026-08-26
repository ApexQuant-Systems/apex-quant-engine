import os
import sys
import time
import sqlite3

# Ensure root directory is in python path for clean imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_pipeline.market_event_bus import MarketEventBus, MarketTickEvent
from research.state_recovery_engine import StateRecoveryEngine
from research.portfolio_coordinator import PortfolioCoordinator
from research.emergency_kill_switch import EmergencyKillSwitch

class PlatformIntegrationHarness:
    """
    🛰️ APEX INFRASTRUCTURE SYSTEM: SPRINT 2 INTEGRATION HARNESS
    Wires independent primitives into a single end-to-end processing pipeline.
    """
    def __init__(self, db_path: str = "data/forward_testing_vault.db"):
        self.db_path = db_path
        self.bus = MarketEventBus()
        self.coordinator = PortfolioCoordinator(db_path=db_path)
        self.kill_switch = EmergencyKillSwitch(db_path=db_path)
        self.recovery = StateRecoveryEngine(db_path=db_path)
        
        # Core State Flags
        self.total_signals_processed = 0
        self.orders_generated = 0

    def initialize_pipeline(self):
        print("🔄 [INTEGRATION] Connecting system modules to the Canonical Event Bus...")
        # Wire our pipeline components to listen to the Event Bus
        self.bus.subscribe("tick", self._database_logger_sink)
        self.bus.subscribe("tick", self._strategy_logic_evaluator)

    def _database_logger_sink(self, event: MarketTickEvent):
        """Test 1 & 2: Verify database persistence directly from the stream."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO market_ticks (timestamp, symbol, price, volume)
            VALUES (?, ?, ?, ?)
        """, (event.timestamp, event.symbol, event.price, event.volume))
        conn.commit()
        conn.close()

    def _strategy_logic_evaluator(self, event: MarketTickEvent):
        """Simulates your frozen logic receiving data and issuing a conditional setup request."""
        self.total_signals_processed += 1
        
        # Simulate an intermediate strategy signal triggering on a specific asset condition
        if event.symbol == "ETHUSDT" and event.price > 3000:
            print(f"  ├── [SIGNAL GENERATED] {event.symbol} condition met. Routing to Risk Perimeter...")
            self._process_order_routing(event.symbol, "LONG", event.price)

    def _process_order_routing(self, symbol: str, direction: str, price: float):
        """Test 3, 4, 5 & 6: Cascades the signal through risk, safety, and execution states."""
        # Test 3: Portfolio Coordinator Check
        if not self.coordinator.evaluate_order_request(symbol, "SET_4_INTRADAY", direction):
            print("  └── ❌ [PIPELINE BLOCK] Order dropped by Portfolio Coordinator.")
            return

        # Test 4: Emergency Kill Switch System Health Audit
        if not self.kill_switch.inspect_system_health():
            print("  └── ❌ [PIPELINE BLOCK] Order dropped by Emergency Kill Switch.")
            return

        # Test 5 & 6: Mock Order Generation and Storage
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        order_id = f"MOCK_ORD_{int(time.time())}"
        
        cursor.execute("""
            INSERT INTO orders (order_id, timestamp, symbol, strategy_set, direction, price, status)
            VALUES (?, ?, ?, 'SET_4_INTRADAY', ?, ?, 'SUBMITTED')
        """, (order_id, int(time.time() * 1000), symbol, direction, price))
        
        conn.commit()
        conn.close()
        
        self.orders_generated += 1
        print(f"  └── 🎉 [MOCK ORDER CREATED & STORED] ID: {order_id} | Filled at: ${price}")

def execute_integration_gauntlet():
    print("=====================================================================")
    print(" 🛰️ APEX PLATFORM: RUNNING INTEGRATION GAUNTLET (SPRINT 2)")
    print("=====================================================================")
    
    db_file = "data/forward_testing_vault.db"
    
    # Reset internal simulation tables to guarantee test runtime integrity
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("DELETE FROM market_ticks;")
    cur.execute("DELETE FROM orders;")
    cur.execute("DELETE FROM positions;")
    cur.execute("DELETE FROM system_events;")
    conn.commit()
    conn.close()

    # Instantiate the unified harness
    harness = PlatformIntegrationHarness()
    harness.initialize_pipeline()
    
    # ----------------------------------------------------------------
    print("\n⚡ Test Sequence 1-6: End-to-End Pipeline Execution Under Normal Load")
    print("-" * 69)
    # Simulate an asset that is currently locked in an active position to trigger coordination filters
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("INSERT INTO positions VALUES ('BTCUSDT', 1718222000000, 68500.0, 67200.0, 73700.0, 0.01, 'ACTIVE');")
    conn.commit()
    conn.close()
    
    # Broadcast an asset event tick that will clear risk parameters
    clean_exchange_packet = '{"e":"24hrMiniTicker","E":1718222001000,"s":"ETHUSDT","c":"3450.00","v":"12.5"}'
    harness.bus.normalize_binance_tick("ETHUSDT", clean_exchange_packet)
    
    # ----------------------------------------------------------------
    print("\n⚡ Test Sequence 7 & 8: Simulated Platform Crash and Recovery Audit")
    print("-" * 69)
    print("⚠️ [CRASH SIMULATION] Severing volatile runtime memory cache strings...")
    del harness  # Memory completely dropped. Volatile state is wiped.
    
    print("🔄 [REBOOT] Initializing clean infrastructure platform structures...")
    rebooted_harness = PlatformIntegrationHarness()
    
    # Run historical state recovery lookup directly against disk WAL files
    recovered_memory = rebooted_harness.recovery.reconstruct_runtime_memory()
    
    print("-" * 69)
    print("🏁 SYSTEM INTEGRATION GAUNTLET VERDICT:")
    if recovered_memory.is_recovered and recovered_memory.pending_order_count == 1:
        print("  🏁 Status: 🟢 SPRINT 2 PASSED — PIPELINE OPERATING HARMONIOUSLY")
    else:
        print("  🏁 Status: 🔴 SPRINT 2 FAILURE — STATE DESYNCHRONIZATION DETECTED")
    print("=====================================================================")

if __name__ == "__main__":
    execute_integration_gauntlet()
