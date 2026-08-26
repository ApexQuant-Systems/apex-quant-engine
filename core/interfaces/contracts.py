from dataclasses import dataclass, field
from typing import List

# PHASE 2: Market Intelligence Output
@dataclass(frozen=True)
class MarketState:
    symbol: str
    timeframe: str
    timestamp: float
    trend: str
    structure: str
    phase: str
    keyzones: List[str]
    liquidity: List[str]
    strength: float
    confidence: float
    invalidated: bool

# PHASE 3: Strategy Output
@dataclass(frozen=True)
class StrategySignal:
    symbol: str
    timestamp: float
    action: str
    htf_bias: str
    mtf_setup: str
    ltf_trigger: str

# PHASE 4: Trade Management Output
@dataclass(frozen=True)
class TradePlan:
    symbol: str
    direction: str
    entry: float
    sl: float
    tp: float
    timestamp: float
    risk_reward: float
    status: str = "PENDING"  # Default field is LAST

# PHASE 5: Risk Output
@dataclass(frozen=True)
class RiskAssessment:
    symbol: str
    timestamp: float
    allowed: bool
    position_size: float
    risk_amount: float
    reason: str = "VALIDATED"  # Default field is LAST
