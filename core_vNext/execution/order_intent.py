from dataclasses import dataclass
from enum import Enum
from typing import Optional

class OrderSide(Enum):
    LONG = 'LONG'
    SHORT = 'SHORT'

@dataclass
class OrderIntent:
    """
    Decouples signal generation from actual exchange execution.
    Contains all the parameters required by the Execution Engine.
    """
    asset: str
    timeframe_set: str
    side: OrderSide
    entry_price: float
    sl_price: float
    tp_price: float
    risk_percentage: float
    strategy_version: str = "vNext-1.0"
    order_type: str = "LIMIT"
    expected_rr: float = 0.0
    status: str = "PENDING_APPROVAL"
