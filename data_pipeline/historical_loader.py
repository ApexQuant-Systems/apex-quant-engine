# filename: data_pipeline/historical_loader.py
import logging
import sqlite3
from datetime import datetime
from typing import List, Any
from config.global_config import GLOBAL_CONFIG
from data_pipeline.exchange_interface import IApexExchangeAdapter
from data_pipeline.data_validator import ApexDataValidator

class ApexHistoricalLoader:
    """
    Module 1.4: Pipeline ingestion engine that drives batch historical queries.
    Utilizes injected adapters and validators to keep components separate.
    """
    def __init__(self, exchange_adapter: IApexExchangeAdapter, validator: ApexDataValidator):
        self.adapter = exchange_adapter
        self.validator = validator
        self.logger = logging.getLogger("ApexHistoricalLoader")

    def download_and_sync(self, symbol: str, normalized_interval: str, limit: int = 100) -> int:
        """Downloads, tests, and commits records cleanly into the storage vault."""
        raw_matrix = self.adapter.fetch_historical_candles(symbol, normalized_interval, limit)
        if not raw_matrix:
            self.logger.warning(f"Adapter returned zero blocks for target instrument: {symbol}")
            return 0

        inserted_rows = 0
        conn = sqlite3.connect(GLOBAL_CONFIG.DB_PATH)
        cursor = conn.cursor()

        # Isolate existing records to prevent unique key constraint conflicts
        cursor.execute(
            "SELECT timestamp FROM candles WHERE symbol=? AND timeframe=?", (symbol, normalized_interval)
        )
        existing_timestamps = {row[0] for row in cursor.fetchall()}

        for candle in raw_matrix:
            # 1. Evaluate through our data validation gate
            is_valid, validation_msg = self.validator.verify_candle_geometry(candle)
            if not is_valid:
                self.logger.error(f"Data anomaly blocked on {symbol}: {validation_msg}")
                continue

            # 2. Convert raw epoch time to human-scannable database chronological index keys
            epoch_seconds = int(candle[0]) / 1000.0
            dt_string = datetime.utcfromtimestamp(epoch_seconds).strftime('%Y-%m-%d %H:%M:%S')

            if dt_string in existing_timestamps:
                continue

            try:
                cursor.execute("""
                    INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, normalized_interval, dt_string,
                    float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4]), float(candle[5])
                ))
                inserted_rows += 1
                existing_timestamps.add(dt_string)
            except sqlite3.IntegrityError:
                continue

        conn.commit()
        conn.close()
        return inserted_rows
