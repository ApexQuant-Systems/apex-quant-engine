from dataclasses import dataclass, field
from typing import List, Dict

@dataclass(frozen=True)
class ApexConfig:
    # Target Assets (Risk Groups)
    symbols: List[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    
    # Generic Timeframe Hierarchy
    timeframes: Dict[str, str] = field(default_factory=lambda: {"A": "4H", "B": "1H", "C": "15M"})
    
    # Capital Protection
    risk_per_trade_pct: float = 1.0
    
    # Storage Paths
    db_path: str = "data/apex_quant.db"

# Instantiate the single global configuration object
GLOBAL_CONFIG = ApexConfig()
