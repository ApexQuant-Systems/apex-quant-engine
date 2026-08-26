import os
import sys
import sqlite3
import time

# Append workspace root directory for clean cross-module importing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class ApexAccountingCore:
    """
    🛰️ APEX STATE ACCOUNTING MATRIX: STAGE H2/H3/H4
    Manages local position synchronization, relational trade journaling,
    and portfolio capital tracking inside the SQLite persistence vault.
    """
    def __init__(self, db_path: str = "data/forward_testing_vault.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._initialize_relational_infrastructure()

    def _initialize_relational_infrastructure(self):
        """Creates institutional auditing tables if they do not exist natively."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. PORTFOLIO BALANCE LEDGER (Stage H4)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_balance (
                asset TEXT PRIMARY KEY,
                available_balance REAL,
                locked_balance REAL,
                updated_timestamp INTEGER
            )
        """)
        
        # 2. ACTIVE POSITION TRACKER (Stage H2)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_positions (
                symbol TEXT PRIMARY KEY,
                size REAL,
                average_entry_price REAL,
                unrealized_pnl REAL,
                last_updated INTEGER
            )
        """)
        
        # 3. COMPREHENSIVE TRADE JOURNAL (Stage H3 - Evidence Receptacle)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_journal (
                trade_id TEXT PRIMARY KEY,
                exchange_order_id INTEGER,
                symbol TEXT,
                strategy_source TEXT,
                setup_pattern TEXT,
                side TEXT,
                execution_qty REAL,
                execution_price REAL,
                total_quote_cost REAL,
                timestamp INTEGER
            )
        """)
        
        # Seed initial mock cash balance for the paper system if table is fresh
        cursor.execute("SELECT COUNT(*) FROM portfolio_balance WHERE asset = 'USDT'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO portfolio_balance (asset, available_balance, locked_balance, updated_timestamp)
                VALUES ('USDT', 10000.0, 0.0, ?)
            """, (int(time.time() * 1000),))
            
        conn.commit()
        conn.close()
        print("  ├── [ACCOUNTING CORE] Database schemas successfully deployed to storage.")

    def record_execution_fill(self, trade_token: str, order_id: int, signal: dict, fill_price: float):
        """Logs execution records cleanly to disk and handles position tracking recalculations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now_ms = int(time.time() * 1000)
        
        symbol = signal["symbol"]
        side = signal["side"].upper()
        qty = signal["quantity"]
        cost = qty * fill_price
        
        try:
            # 1. Commit the historical row to the Trade Journal
            cursor.execute("""
                INSERT INTO trade_journal (trade_id, exchange_order_id, symbol, strategy_source, setup_pattern, side, execution_qty, execution_price, total_quote_cost, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (trade_token, order_id, symbol, signal["source"], signal["setup"], side, qty, fill_price, cost, now_ms))
            
            # 2. Reconcile Active Position Inventory Layer (Simplified buy mapping calculation)
            if side == "BUY":
                cursor.execute("SELECT size, average_entry_price FROM active_positions WHERE symbol = ?", (symbol,))
                row = cursor.fetchone()
                
                if row is None:
                    cursor.execute("""
                        INSERT INTO active_positions (symbol, size, average_entry_price, unrealized_pnl, last_updated)
                        VALUES (?, ?, ?, 0.0, ?)
                    """, (symbol, qty, fill_price, now_ms))
                else:
                    current_size, current_avg = row
                    new_size = current_size + qty
                    new_avg = ((current_size * current_avg) + cost) / new_size
                    cursor.execute("""
                        UPDATE active_positions 
                        SET size = ?, average_entry_price = ?, last_updated = ?
                        WHERE symbol = ?
                    """, (new_size, new_avg, now_ms, symbol))
                    
                # 3. Deduct transaction cost from portfolio capital pools
                cursor.execute("""
                    UPDATE portfolio_balance 
                    SET available_balance = available_balance - ? 
                    WHERE asset = 'USDT'
                """, (cost,))
                
            conn.commit()
            print(f"  ├── [JOURNALED] Trade record {trade_token} safely locked to SQLite database.")
        except Exception as e:
            print(f"  ❌ [ACCOUNTING CORE ERROR] Storage write failure: {e}")
        finally:
            conn.close()

    def print_account_status_report(self):
        """Queries relational records directly from disk to output a structured core report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("\n=====================================================================")
        print(" 🛰️  APEX CORE REPORT: RELATIONAL POSITION & PORTFOLIO LEDGER STATUS")
        print("=====================================================================")
        
        cursor.execute("SELECT asset, available_balance FROM portfolio_balance")
        for asset, bal in cursor.fetchall():
            print(f"💰 Account Cash Reserve : {bal:,.2f} {asset}")
            
        print("-" * 69)
        print("📋 ACTIVE EXPOSITION RUNTIME MATRIX:")
        cursor.execute("SELECT symbol, size, average_entry_price FROM active_positions")
        positions = cursor.fetchall()
        if not positions:
            print("  └── No active tracking positions found on disk database storage.")
        for sym, size, avg in positions:
            print(f"  ├── Asset Position: {sym:<9} | Allocation Size: {size:<6} | Average Cost: ${avg:,.2f}")
            
        print("-" * 69)
        print("📖 HISTORICAL AUDITING ENTRIES LOGGED:")
        cursor.execute("SELECT trade_id, strategy_source, side, execution_qty, execution_price FROM trade_journal")
        for tid, src, side, qty, px in cursor.fetchall():
            print(f"  ├── ID: {tid} | Source: {src:<20} | {side:<4} {qty} @ ${px:,.2f}")
        print("=====================================================================\n")
        conn.close()

if __name__ == "__main__":
    accounting = ApexAccountingCore()
    
    # Run an initial structural data generation trace simulation
    mock_signal = {
        "source": "APEX_SET_4_INTRADAY",
        "setup": "15M_OB_LIQUIDITY_SWEEP",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.01
    }
    
    print("⚡ Triggering sample validation trade logging event...")
    accounting.record_execution_fill(
        trade_token="TX_999_INITIAL_TEST",
        order_id=4411018,
        signal=mock_signal,
        fill_price=64089.78
    )
    
    accounting.print_account_status_report()
