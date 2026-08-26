import sqlite3
import os

class PortfolioCoordinator:
    """
    🛰️ APEX RISK INFRASTRUCTURE: MULTI-HORIZON PORTFOLIO COORDINATOR
    Enforces the global 6-slot ceiling, checks for asset duplication,
    and coordinates simultaneous strategy execution across timeframes.
    """
    def __init__(self, db_path: str = "data/forward_testing_vault.db", max_global_slots: int = 6):
        self.db_path = db_path
        self.max_global_slots = max_global_slots

    def evaluate_order_request(self, symbol: str, strategy_set: str, direction: str) -> bool:
        if not os.path.exists(self.db_path):
            print("  ❌ [COORD REJECTION] Database vault offline.")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. Enforce Global Slot Ceiling Law
        cursor.execute("SELECT COUNT(*) FROM positions WHERE status='ACTIVE'")
        active_slots = cursor.fetchone()[0]

        if active_slots >= self.max_global_slots:
            print(f"  ❌ [COORD REJECTION] Global exposure ceiling breach. Active slots: {active_slots}/{self.max_global_slots}")
            conn.close()
            return False

        # 2. Prevent Intraday Duplication Overlapping Same-Direction Asset
        # If SET_2 is already Long BTC, SET_4 Intraday is blocked from scaling into the same direction.
        cursor.execute("SELECT COUNT(*) FROM positions WHERE symbol=? AND status='ACTIVE'", (symbol,))
        existing_asset_trades = cursor.fetchone()[0]

        if existing_asset_trades > 0:
            print(f"  ❌ [COORD REJECTION] Risk block. {symbol} already holds an active position slot.")
            conn.close()
            return False

        conn.close()
        print(f"  🟢 [COORD APPROVED] Order request cleared for {symbol} via [{strategy_set}] ({direction})")
        return True

if __name__ == "__main__":
    print("=====================================================================")
    print(" 🛰️ APEX RISK INFRASTRUCTURE: TESTING SIMULTANEOUS TRIGGER FILTERS")
    print("=====================================================================")
    
    coordinator = PortfolioCoordinator()
    
    # Simulation Scenario A: Intraday engine tries to enter BTC while a position is already active
    print("⚡ Scenario A: SET_4 requests BTC Long while State Engine holds an active BTC slot...")
    coordinator.evaluate_order_request(symbol="BTCUSDT", strategy_set="SET_4_INTRADAY", direction="LONG")
    
    # Simulation Scenario B: Strategy requests an entry on a completely fresh asset (ETH)
    print("\n⚡ Scenario B: SET_2 requests ETH Long on an open, unallocated portfolio slot...")
    coordinator.evaluate_order_request(symbol="ETHUSDT", strategy_set="SET_2_MEDIUM_SWING", direction="LONG")
    print("=====================================================================")
