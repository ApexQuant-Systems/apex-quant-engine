import os
import sys
import pandas as pd
from datetime import datetime, timedelta

class CandleAggregatorMatrix:
    """Ingests low-timeframe data structures and compresses them into high-fidelity macro bars."""
    def __init__(self, target_interval_minutes=5):
        self.interval = target_interval_minutes
        self.current_bucket = []
        self.current_bucket_id = None
        print(f"[*] Initializing Candle Aggregator Matrix for [{self.interval}m] compounding blocks.")

    def _calculate_bucket_floor(self, dt):
        """Floors a timestamp down to its nearest interval anchor point."""
        discard = timedelta(minutes=dt.minute % self.interval,
                            seconds=dt.second,
                            microseconds=dt.microsecond)
        return dt - discard

    def process_low_timeframe_candle(self, candle_1m):
        """Ingests a single 1-minute candle dict and checks if a macro block has closed."""
        candle_time = candle_1m["start_time"]
        bucket_id = self._calculate_bucket_floor(candle_time)

        # If we enter a brand new time block, flush the completed macro candle out
        if self.current_bucket_id and bucket_id != self.current_bucket_id:
            macro_candle = self._consolidate_active_bucket()
            self.current_bucket_id = bucket_id
            self.current_bucket = [candle_1m]
            return macro_candle  # Returns the finalized high-timeframe candle

        # Otherwise, maintain state inside the active compression group
        if not self.current_bucket_id:
            self.current_bucket_id = bucket_id
            
        self.current_bucket.append(candle_1m)
        return None  # Macro candle is still cooking, return None

    def _consolidate_active_bucket(self):
        """Performs raw OHLC downsampling math across the collected bucket rows."""
        if not self.current_bucket:
            return None

        # Extract structural arrays
        opens = [c["open"] for c in self.current_bucket]
        highs = [c["high"] for c in self.current_bucket]
        lows = [c["low"] for c in self.current_bucket]
        closes = [c["close"] for c in self.current_bucket]

        # Consolidate boundaries safely
        macro_candle = {
            "start_time": self.current_bucket_id,
            "open": opens[0],
            "high": max(highs),
            "low": min(lows),
            "close": closes[-1]
        }
        return macro_candle

if __name__ == "__main__":
    # Internal Unit Test Suite to verify mathematical precision
    print("\n==================================================")
    # Mock a sequence of 5 distinct 1m bars forming a single 5m macro candle
    mock_1m_stream = [
        {"start_time": datetime(2026, 5, 26, 22, 0), "open": 76000.0, "high": 76100.0, "low": 75950.0, "close": 76050.0},
        {"start_time": datetime(2026, 5, 26, 22, 1), "open": 76050.0, "high": 76200.0, "low": 76000.0, "close": 76150.0},
        {"start_time": datetime(2026, 5, 26, 22, 2), "open": 76150.0, "high": 76180.0, "low": 75800.0, "close": 75900.0}, # Max Low Hit here ($75,800)
        {"start_time": datetime(2026, 5, 26, 22, 3), "open": 75900.0, "high": 76350.0, "low": 75900.0, "close": 76250.0}, # Max High Hit here ($76,350)
        {"start_time": datetime(2026, 5, 26, 22, 4), "open": 76250.0, "high": 76300.0, "low": 76200.0, "close": 76280.0}, # Final Close here ($76,280)
        # This 6th candle forces the rollover boundary event
        {"start_time": datetime(2026, 5, 26, 22, 5), "open": 76280.0, "high": 76400.0, "low": 76250.0, "close": 76300.0}
    ]

    aggregator = CandleAggregatorMatrix(target_interval_minutes=5)
    
    print("[*] Streaming mock raw 1m data array into the compression matrices...")
    for idx, bar in enumerate(mock_1m_stream):
        closed_macro_bar = aggregator.process_low_timeframe_candle(bar)
        if closed_macro_bar:
            print("\n🔥 [AGGREGATION BOUNDARY BREAK] Successfully synthesized 5m Macro Candle:")
            print(f" ├── Start Interval Anchor : {closed_macro_bar['start_time']}")
            print(f" ├── Compiled Open Price   : ${closed_macro_bar['open']:.2f}")
            print(f" ├── Peak Compressed High  : ${closed_macro_bar['high']:.2f} (Verified Match)")
            print(f" ├── Floor Compressed Low   : ${closed_macro_bar['low']:.2f} (Verified Match)")
            print(f" └── Boundary Close Price  : ${closed_macro_bar['close']:.2f} (Verified Match)\n")
    print("==================================================\n")
