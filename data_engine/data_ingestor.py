# filename: data_engine/data_ingestor.py
import requests
import sqlite3
from typing import List
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.global_config import GLOBAL_CONFIG
from core.logger import APEX_LOGGER

class DataIngestor:
    def __init__(self):
        self.db_path = GLOBAL_CONFIG.db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                symbol TEXT,
                timeframe TEXT,
                timestamp INTEGER,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        ''')
        conn.commit()
        conn.close()

    def ingest_batch(self, symbols: List[str], timeframes: List[str], limit: int = 1000):
        for symbol in symbols:
            for tf in timeframes:
                APEX_LOGGER.info(f"Ingesting {symbol} on {tf}...")
                records = self.fetch_ohlcv(symbol, tf, limit)
                self.store_data(records)
        APEX_LOGGER.info("Batch ingestion complete.")

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[tuple]:
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": timeframe, "limit": limit}
        response = requests.get(url, params=params)
        if response.status_code != 200: return []
        data = response.json()
        return [(symbol, timeframe, int(d[0]), float(d[1]), float(d[2]), float(d[3]), float(d[4]), float(d[5])) for d in data]

    def store_data(self, records: List[tuple]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR IGNORE INTO market_data 
            (symbol, timeframe, timestamp, open, high, low, close, volume) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)
        conn.commit()
        conn.close()
