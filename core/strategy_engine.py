from dataclasses import dataclass
from core.interfaces.contracts import MarketState, StrategySignal
import time

class StrategyEngine:
    def generate_signal(self, htf: MarketState, mtf: MarketState, ltf: MarketState) -> StrategySignal:
        bias = htf.trend
        
        # New: Allow trade even if NEUTRAL (Range Trading)
        setup_ready = True 
        
        # Keep existing sweep logic
        action = "WAIT"
        if setup_ready:
            if "EQH_SWEEP" in ltf.liquidity or "EQL_SWEEP" in ltf.liquidity:
                action = "BUY" if bias != "BEARISH" else "SELL"
        
        return StrategySignal(ltf.symbol, time.time(), action, htf.trend, mtf.phase, ltf.structure)
