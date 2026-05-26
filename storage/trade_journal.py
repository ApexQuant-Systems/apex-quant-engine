import sqlite3
import os
from datetime import datetime

class TradeJournalDB:
    def __init__(self, db_name="storage/apex_systems.db"):
        self.db_name = db_name
        self.initialize_database()

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def initialize_database(self):
        """Creates the persistent database tables if they do not exist on the disk space."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_time TEXT,
                    exit_time TEXT,
                    side TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    sl REAL,
                    tp REAL,
                    size REAL,
                    risk_capital REAL,
                    pnl REAL,
                    exit_reason TEXT,
                    regime TEXT,
                    displacement_ratio REAL,
                    conviction_score INTEGER,
                    status TEXT
                )
            """)
            conn.commit()

    def get_active_position(self) -> dict:
        """Queries the storage layer for an open transaction row to facilitate rehydration loops."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row  # Maps column headers directly to dictionary keys
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trade_journal WHERE status = 'ACTIVE' LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def write_trade_entry(self, side: str, entry_price: float, sl: float, tp: float, size: float, risk_capital: float, regime: str, ratio: float, score: int, timestamp: datetime) -> int:
        """Persists a newly instantiated live position right to the hardware layer."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trade_journal (
                    entry_time, side, entry_price, sl, tp, size, risk_capital, regime, displacement_ratio, conviction_score, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (timestamp.strftime("%Y-%m-%d %H:%M:%S"), side, entry_price, sl, tp, size, risk_capital, regime, ratio, score))
            conn.commit()
            return cursor.lastrowid

    def write_trade_exit(self, trade_id: int, exit_price: float, pnl: float, reason: str, timestamp: datetime):
        """Finalizes a tracking row inside the database, recording absolute performance metrics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trade_journal 
                SET exit_time = ?, exit_price = ?, pnl = ?, exit_reason = ?, status = 'CLOSED'
                WHERE id = ?
            """, (timestamp.strftime("%Y-%m-%d %H:%M:%S"), exit_price, pnl, reason, trade_id))
            conn.commit()
