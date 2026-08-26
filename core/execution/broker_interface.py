# filename: core/execution/broker_interface.py
from abc import ABC, abstractmethod
from core.interfaces.contracts import TradePlan

class BrokerAdapter(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def place_order(self, plan: TradePlan) -> str:
        """Returns Order ID or Error string."""
        pass

    @abstractmethod
    def get_account_balance(self) -> float:
        pass
