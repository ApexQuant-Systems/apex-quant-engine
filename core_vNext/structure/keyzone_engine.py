import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class KeyzoneType(Enum):
    FVG_BULLISH = 'FVG_BULLISH'
    FVG_BEARISH = 'FVG_BEARISH'
    OB_BULLISH = 'OB_BULLISH'
    OB_BEARISH = 'OB_BEARISH'

@dataclass
class Keyzone:
    index: int
    timestamp: float
    zone_type: KeyzoneType
    top: float
    bottom: float
    mitigated: bool = False
    mitigated_at_index: Optional[int] = None

class KeyzoneEngine:
    """
    Identifies Order Blocks and Fair Value Gaps. Tracks mitigation state dynamically.
    """
    def __init__(self, mitigation_mode: str = 'full_overlap'):
        self.mitigation_mode = mitigation_mode
        self.zones: List[Keyzone] = []
        self.active_zones: List[Keyzone] = []

    def reset(self):
        self.zones = []
        self.active_zones = []

    def process_batch(self, df: pd.DataFrame):
        self.reset()
        if len(df) < 3:
            return

        highs = df['high'].values
        lows = df['low'].values
        timestamps = df['timestamp'].values
        
        for i in range(2, len(df)):
            self._evaluate_step(i, timestamps, highs, lows)

    def _evaluate_step(self, i: int, timestamps: np.ndarray, highs: np.ndarray, lows: np.ndarray):
        # 1. Evaluate Mitigation of existing active zones only (O(1) active set)
        current_high = highs[i]
        current_low = lows[i]

        remaining_active = []
        for zone in self.active_zones:
            mitigated = False
            if self.mitigation_mode == 'full_overlap':
                if zone.zone_type in [KeyzoneType.FVG_BULLISH, KeyzoneType.OB_BULLISH]:
                    if current_low < zone.bottom:
                        mitigated = True
                else: # BEARISH
                    if current_high > zone.top:
                        mitigated = True
            elif self.mitigation_mode == 'touch':
                if zone.zone_type in [KeyzoneType.FVG_BULLISH, KeyzoneType.OB_BULLISH]:
                    if current_low <= zone.top:
                        mitigated = True
                else: # BEARISH
                    if current_high >= zone.bottom:
                        mitigated = True

            if mitigated:
                zone.mitigated = True
                zone.mitigated_at_index = i
            else:
                remaining_active.append(zone)

        self.active_zones = remaining_active

        # 2. Detect New FVGs
        # Bullish FVG: low of candle i > high of candle i-2
        if lows[i] > highs[i-2]:
            new_fvg = Keyzone(
                index=i,
                timestamp=timestamps[i],
                zone_type=KeyzoneType.FVG_BULLISH,
                top=lows[i],
                bottom=highs[i-2]
            )
            self.zones.append(new_fvg)
            self.active_zones.append(new_fvg)
            
        # Bearish FVG: high of candle i < low of candle i-2
        elif highs[i] < lows[i-2]:
            new_fvg = Keyzone(
                index=i,
                timestamp=timestamps[i],
                zone_type=KeyzoneType.FVG_BEARISH,
                top=lows[i-2],
                bottom=highs[i]
            )
            self.zones.append(new_fvg)
            self.active_zones.append(new_fvg)

    def get_active_zones(self) -> List[Keyzone]:
        return self.active_zones
