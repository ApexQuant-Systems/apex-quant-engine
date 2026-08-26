# filename: data_pipeline/storage_manager.py
import logging
import sqlite3
from typing import List, Any, Dict
from config.global_config import GLOBAL_CONFIG

class ApexStorageManager:
    """
    Module 1.7: High-level database abstraction layer. 
    Insulates upper layers from raw SQL interactions and ensures clean data formatting.
    """
    def __init__(self):
        self.db_path = GLOBAL_CONFIG.DB_PATH
        self.logger = logging.getLogger("ApexStorageManager")

    def get_historical_candles(self, symbol: str, timeframe: str, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Retrieves historical candlesticks in strict chronological order.
        Returns a uniform list of structured dictionaries.
        """
        conn = sqlite3.connect(self.db_path)
        # Configure row factory to return clean column key maps
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT timestamp, open, high, low, close, volume 
                FROM candles 
                WHERE symbol = ? AND timeframe = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (symbol.upper(), timeframe, limit))
            
            rows = cursor.fetchall()
            # Reverse rows to return data in chronological ascending order
            candles_matrix = [dict(row) for row in rows][::-1]
            return candles_matrix
        except Exception as e:
            self.logger.error(f"Failed to query storage tables for {symbol}: {str(e)}")
            return []
        finally:
            conn.close()
