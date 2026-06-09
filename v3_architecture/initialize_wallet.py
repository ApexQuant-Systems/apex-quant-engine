import sqlite3
import os

DB_PATH = "./data/forward_testing_vault.db"

def build_paper_wallet_vault():
    """Initializes a persistent paper cash ledger to handle decoupled account balances."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create account balance ledger
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_wallet (
            account_id TEXT PRIMARY KEY,
            balance REAL,
            initial_capital REAL,
            currency TEXT,
            updated_at TEXT
        )
    ''')
    
    # Seed account with a clean $30,000.00 base if it doesn't already exist
    cursor.execute("SELECT COUNT(*) FROM paper_wallet")
    if cursor.fetchone()[0] == 0:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if 'datetime' in locals() else "2026-06-09 12:00:00"
        cursor.execute('''
            INSERT INTO paper_wallet (account_id, balance, initial_capital, currency, updated_at)
            VALUES ('APEX_PAPER_01', 30000.0, 30000.0, 'USD', ?)
        ''', (timestamp,))
        print("💰 Paper Capital Ledger successfully provisioned with a secure $30,000.00 cash base.")
    else:
        print("ℹ️ Existing Paper Capital Ledger detected. Skipping re-seeding to protect operational data.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    build_paper_wallet_vault()
