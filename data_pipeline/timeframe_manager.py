# filename: data_pipeline/timeframe_manager.py
import logging
from typing import List, Dict
from config.global_config import GLOBAL_CONFIG

class ApexTimeframeManager:
    """
    Module 1.2: Normalizes and structures multi-timeframe horizons.
    Prevents downstream strategy processing errors due to interval misalignment.
    """
    def __init__(self):
        self.logger = logging.getLogger("ApexTimeframeManager")
        self._interval_mappings: Dict[str, str] = {
            "15M": "15m", "1H": "1h", "4H": "4h", "1D": "1d", "1W": "1w", "1M": "1M"
        }

    def normalize_interval(self, timeframe: str) -> str:
        """Converts internal timeframe signatures to standard lowercase API formats."""
        upper_tf = timeframe.upper()
        if upper_tf not in self._interval_mappings:
            self.logger.error(f"Unsupported timeframe format requested: {timeframe}")
            raise ValueError(f"Timeframe {timeframe} is completely foreign to Apex OS contracts.")
        return self._interval_mappings[upper_tf]

    def get_horizon_timeframes(self, horizon_set: int) -> List[str]:
        """Returns the specific multi-timeframe horizon alignment array parameters."""
        if horizon_set == 1:
            return GLOBAL_CONFIG.SET_1_INVESTMENT
        elif horizon_set == 2:
            return GLOBAL_CONFIG.SET_2_SWING
        elif horizon_set == 3:
            return GLOBAL_CONFIG.SET_3_POSITION
        elif horizon_set == 4:
            return GLOBAL_CONFIG.SET_4_INTRADAY
        else:
            raise ValueError(f"Horizon parameter Set {horizon_set} does not exist.")
