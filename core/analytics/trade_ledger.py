import sqlite3
from core.interfaces.contracts import TradePlan

class TradeLedger:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_ledger()

    def _init_ledger(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                direction TEXT,
                entry REAL,
                sl REAL,
                tp REAL,
                status TEXT,
                rr REAL,
                timestamp REAL
            )
        ''')
        conn.commit()
        conn.close()

    def record_trade(self, plan: TradePlan):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trade_ledger 
            (symbol, direction, entry, sl, tp, status, rr, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (plan.symbol, plan.direction, plan.entry, plan.sl, plan.tp, plan.status, plan.risk_reward, plan.timestamp))
        conn.commit()
        conn.close()
