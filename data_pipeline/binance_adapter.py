# filename: data_pipeline/binance_adapter.py
import json
import urllib.request
import logging
from typing import List, Any
from data_pipeline.exchange_interface import IApexExchangeAdapter

class BinanceExchangeAdapter(IApexExchangeAdapter):
    """
    Concrete network interface wrapper for the Binance public REST architecture.
    Completely isolated inside the adapter boundary line.
    """
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3/klines"
        self.logger = logging.getLogger("BinanceAdapter")

    def fetch_historical_candles(self, symbol: str, normalized_interval: str, limit: int) -> List[List[Any]]:
        """Queries the network cluster and parses structural arrays into clean list format."""
        url = f"{self.base_url}?symbol={symbol.upper()}&interval={normalized_interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'ApexOS-Quant-Engine'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    raw_data = json.loads(response.read().decode())
                    standardized_matrix = []
                    for row in raw_data:
                        # Normalize structural response indexes: [OpenTime, O, H, L, C, V]
                        standardized_matrix.append([
                            row[0],  # Open Epoch Milliseconds
                            row[1],  # Open Price String
                            row[2],  # High Price String
                            row[3],  # Low Price String
                            row[4],  # Close Price String
                            row[5]   # Volume Volume String
                        ])
                    return standardized_matrix
                else:
                    self.logger.error(f"Network error status returned from matching cluster: {response.status}")
        except Exception as e:
            self.logger.error(f"Critical data link error processing {symbol}: {str(e)}")
        return []
