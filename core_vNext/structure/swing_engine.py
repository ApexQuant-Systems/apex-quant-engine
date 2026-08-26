import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class SwingType(Enum):
    HIGH = 'HIGH'
    LOW = 'LOW'

class Trend(Enum):
    BULLISH = 'BULLISH'
    BEARISH = 'BEARISH'
    NEUTRAL = 'NEUTRAL'

@dataclass
class StructuralSwing:
    index: int
    timestamp: float
    price: float
    type: SwingType
    strong: bool = False
    invalidated: bool = False

@dataclass
class StructuralEvent:
    index: int
    timestamp: float
    event_type: str # 'BOS_BULLISH', 'BOS_BEARISH', 'CHOCH_BULLISH', 'CHOCH_BEARISH'
    price_level: float
    trigger_swing: StructuralSwing

class SwingEngine:
    """
    HTF Market Structure Engine: deterministic swings, BOS, CHoCH, and strong/weak classifications.
    Operates on a defined lookback/lookforward window k.
    """
    def __init__(self, k: int = 3):
        self.k = k
        self.reset()

    def reset(self):
        self.highs: List[StructuralSwing] = []
        self.lows: List[StructuralSwing] = []
        self.events: List[StructuralEvent] = []
        self.current_trend = Trend.NEUTRAL
        self.last_confirmed_high: Optional[StructuralSwing] = None
        self.last_confirmed_low: Optional[StructuralSwing] = None

    def process_batch(self, df: pd.DataFrame):
        """
        Processes a batch of historical data to build the initial structural state.
        Expects columns: 'timestamp', 'open', 'high', 'low', 'close'
        """
        self.reset()
        if len(df) < (self.k * 2) + 1:
            return

        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        timestamps = df['timestamp'].values
        
        # Iterate and build state step-by-step to simulate real-time processing
        for i in range(self.k, len(df)):
            self._evaluate_step(i, timestamps, highs, lows, closes)

    def _evaluate_step(self, i: int, timestamps: np.ndarray, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray):
        """
        Evaluate structure at index i, looking back k steps for confirmation.
        A swing at index i-k is confirmed at index i.
        """
        target_idx = i - self.k
        
        # Check if target_idx is a Swing High
        if target_idx >= self.k:
            is_high = True
            target_high = highs[target_idx]
            for j in range(target_idx - self.k, target_idx + self.k + 1):
                if j != target_idx and highs[j] >= target_high:
                    is_high = False
                    break
            
            if is_high:
                new_high = StructuralSwing(target_idx, timestamps[target_idx], target_high, SwingType.HIGH)
                self.highs.append(new_high)
                self.last_confirmed_high = new_high

            # Check if target_idx is a Swing Low
            is_low = True
            target_low = lows[target_idx]
            for j in range(target_idx - self.k, target_idx + self.k + 1):
                if j != target_idx and lows[j] <= target_low:
                    is_low = False
                    break
            
            if is_low:
                new_low = StructuralSwing(target_idx, timestamps[target_idx], target_low, SwingType.LOW)
                self.lows.append(new_low)
                self.last_confirmed_low = new_low

        # Check for Structural Breaks (BOS / CHoCH)
        # Structural breaks happen in real-time on candle close
        current_close = closes[i]
        
        if self.current_trend in [Trend.NEUTRAL, Trend.BULLISH]:
            # Look for bearish break
            if self.last_confirmed_low and not self.last_confirmed_low.invalidated:
                if current_close < self.last_confirmed_low.price:
                    self.last_confirmed_low.invalidated = True
                    event_type = 'CHOCH_BEARISH' if self.current_trend == Trend.BULLISH else 'BOS_BEARISH'
                    event = StructuralEvent(i, timestamps[i], event_type, self.last_confirmed_low.price, self.last_confirmed_low)
                    self.events.append(event)
                    self.current_trend = Trend.BEARISH
                    
                    # The high that caused this break is now a Strong High
                    if self.last_confirmed_high:
                        self.last_confirmed_high.strong = True

        if self.current_trend in [Trend.NEUTRAL, Trend.BEARISH]:
            # Look for bullish break
            if self.last_confirmed_high and not self.last_confirmed_high.invalidated:
                if current_close > self.last_confirmed_high.price:
                    self.last_confirmed_high.invalidated = True
                    event_type = 'CHOCH_BULLISH' if self.current_trend == Trend.BEARISH else 'BOS_BULLISH'
                    event = StructuralEvent(i, timestamps[i], event_type, self.last_confirmed_high.price, self.last_confirmed_high)
                    self.events.append(event)
                    self.current_trend = Trend.BULLISH
                    
                    # The low that caused this break is now a Strong Low
                    if self.last_confirmed_low:
                        self.last_confirmed_low.strong = True

    def get_state(self) -> Dict[str, Any]:
        return {
            "trend": self.current_trend.value,
            "last_high": self.last_confirmed_high,
            "last_low": self.last_confirmed_low,
            "events_count": len(self.events),
            "latest_event": self.events[-1] if self.events else None
        }
