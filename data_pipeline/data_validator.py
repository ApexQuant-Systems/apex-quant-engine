# filename: data_pipeline/data_validator.py
import logging
from typing import List, Any, Tuple

class ApexDataValidator:
    """
    Module 1.6: Strict math verification engine checking candlestick rows
    for structural abnormalities, out-of-bounds metrics, or data gaps.
    """
    def __init__(self):
        self.logger = logging.getLogger("ApexDataValidator")

    def verify_candle_geometry(self, row: List[Any]) -> Tuple[bool, str]:
        """Validates standard OHLCV index blocks for structural corruption."""
        if not row or len(row) < 6:
            return False, "ERR_INVALID_ARRAY_LENGTH"

        try:
            ts = int(row[0])
            o = float(row[1])
            h = float(row[2])
            l = float(row[3])
            c = float(row[4])
            v = float(row[5])
        except (ValueError, TypeError):
            return False, "ERR_TYPE_COERCION_FAILURE"

        # Boundary condition filters
        if ts <= 0:
            return False, "ERR_INVALID_TIMESTAMP"
        if min(o, h, l, c, v) < 0.0:
            return False, "ERR_NEGATIVE_VALUE_DETECTED"
        if l > h:
            return False, "ERR_GEOMETRIC_INVERSION_LOW_ABOVE_HIGH"
        if o > h or c > h:
            return False, "ERR_GEOMETRIC_OPEN_CLOSE_EXCEEDS_HIGH"
        if o < l or c < l:
            return False, "ERR_GEOMETRIC_OPEN_CLOSE_DROPS_BELOW_LOW"

        return True, "PASSED"
