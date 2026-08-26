# filename: data_pipeline/exchange_interface.py
from abc import ABC, abstractmethod
from typing import List, Any

class IApexExchangeAdapter(ABC):
    """
    Module 1.3: Immutable Interface definition for all exchange communication wrappers.
    Ensures that the Core Data Loader completely strips away venue-specific data structures.
    """
    
    @abstractmethod
    def fetch_historical_candles(self, symbol: str, normalized_interval: str, limit: int) -> List[List[Any]]:
        """
        Abstract gateway querying remote APIs. 
        Must return a standardized sequential grid: 
        [[open_time, open, high, low, close, volume], ...]
        """
        pass
