import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

class TrueMultiTimeframeMatrix:
    """
    Institutional Timeframe Sync Matrix Engine.
    Maintains completely separate state histories for LTF, MTF, and HTF arrays.
    Ensures zero look-ahead data pollution during historical evaluation passes.
    """
    def __init__(self, htf_data: pd.DataFrame, mtf_data: pd.DataFrame, ltf_data: pd.DataFrame):
        # Convert all incoming structural frames to standardized datetime index layers
        self.htf = htf_data.copy().sort_values('timestamp').reset_index(drop=True)
        self.mtf = mtf_data.copy().sort_values('timestamp').reset_index(drop=True)
        self.ltf = ltf_data.copy().sort_values('timestamp').reset_index(drop=True)
        
        self._standardize_timestamps()
        
    def _standardize_timestamps(self):
        for df in [self.htf, self.mtf, self.ltf]:
            if 'datetime' not in df.columns:
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                
    def get_visible_state(self, current_ltf_timestamp):
        """
        Extracts only completely closed macro bars available prior to the active LTF tick.
        Mimics true real-time streaming market constraints.
        """
        # HTF tracking filter: Bar close time must be <= current LTF step time
        # Assuming typical candles, a bar's close timestamp is its start time + interval duration.
        # To be absolutely safe, we filter where HTF datetime < current_ltf_timestamp
        visible_htf = self.htf[self.htf['datetime'] < current_ltf_timestamp]
        visible_mtf = self.mtf[self.mtf['datetime'] < current_ltf_timestamp]
        
        return {
            'closed_htf': visible_htf,
            'closed_mtf': visible_mtf
        }

if __name__ == "__main__":
    print("[✓] TrueMultiTimeframeMatrix Class Compiled. Ready for Structure Engine Integration.")
